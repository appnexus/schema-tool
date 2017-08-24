// <--
// Copyright © 2017 AppNexus Inc.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// -->

package chain

import (
	"bufio"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"path"
	"regexp"
	"strings"

	"github.com/appnexus/schema-tool/log"
)

// Direction of either Up or Down that alter can represent, defined below
type Direction int

const (
	// Undefined direction is used as a placeholder or as an error when
	// parsing directions from alters.
	Undefined Direction = iota

	// Up direction represents an alter that progresses a schema forward
	// and represents new change.
	Up

	// Down direction represents the undoing of an Up alter and is a change
	// that represents negative progress.
	Down
)

// Alter represents a single file within a chain along with the meta-data
// parsed from the file's headers.
type Alter struct {
	FileName  string
	Direction Direction

	// Internal temporary values used to build the chain
	ref     string
	backRef string

	// skipped and required environments. Not exported at the alter-level
	// because validations must be completed at the AlterGroup level and
	// the information is duplicated there.
	requireEnv []string
	skipEnv    []string
}

func newDefaultAlter() *Alter {
	return &Alter{
		Direction:  Undefined,
		requireEnv: make([]string, 0, 4),
		skipEnv:    make([]string, 0, 4),
	}
}

// AlterGroup represents and up/down pair of Alter objects along with links to
// "forward" (child) and "back" (parent) AlterGroup objects.
type AlterGroup struct {
	Up         *Alter
	Down       *Alter
	ForwardRef *AlterGroup
	BackRef    *AlterGroup
	RequireEnv []string
	SkipEnv    []string
}

type Chain struct {
	Head *AlterGroup
	Tail *AlterGroup
}

type InvalidMetaDataError string

func (i InvalidMetaDataError) Error() string {
	return string(i)
}

type DuplicateRefError string

func (d DuplicateRefError) Error() string {
	return string(d)
}

type InvalidChainError string

func (i InvalidChainError) Error() string {
	return string(i)
}

// Given an initial scan of a schema-directory and a list of AlterGroup
// objects, stitch them together into a chain and validate that everything
// looks peachy.
func BuildAndValidateChain(groups map[string]*AlterGroup) (*Chain, error) {

	for _, group := range groups {
		// Validate groups have up/down pair
		if group.Up == nil || group.Down == nil {
			missingDirection := "down"
			other := group.Up
			if group.Up == nil {
				missingDirection = "up"
				other = group.Down
			}
			return nil, InvalidChainError(fmt.Sprintf("Missing %s alter for '%s'",
				missingDirection, other.ref))
		}

		// validate matching back-ref's
		if group.Up.backRef != group.Down.backRef {
			return nil, InvalidChainError(fmt.Sprintf("'back-ref' values for %s do not match (%s and %s)",
				group.Up.ref, group.Up.backRef, group.Down.backRef))
		}

		// Validate skip-env(s) for group
		if len(group.Up.skipEnv) != len(group.Down.skipEnv) {
			return nil, InvalidChainError(fmt.Sprintf(
				"Different number of skip-env's found in:\n"+
					"\t%s\n\t%s\n"+
					"These files must contain the same skip-env values.",
				group.Up.FileName, group.Down.FileName))
		}
		for _, skipUp := range group.Up.skipEnv {
			found := false
			for _, skipDown := range group.Down.skipEnv {
				if skipUp == skipDown {
					found = true
					break
				}
			}
			if !found {
				return nil, InvalidChainError(fmt.Sprintf(
					"skip-env value '%s' is not found in both up & down alters", skipUp))
			}
		}
		group.SkipEnv = group.Up.skipEnv

		// Validate require-env(s) for group
		if len(group.Up.requireEnv) != len(group.Down.requireEnv) {
			return nil, InvalidChainError(fmt.Sprintf(
				"Uneven number of require-env's found in '%s' and '%s'",
				group.Up.FileName, group.Down.FileName))
		}
		for _, requireUp := range group.Up.requireEnv {
			found := false
			for _, requireDown := range group.Down.requireEnv {
				if requireUp == requireDown {
					found = true
					break
				}
			}
			if !found {
				return nil, InvalidChainError(fmt.Sprintf(
					"require-env value '%s' is not found in both up & down alters", requireUp))
			}
		}
		group.RequireEnv = group.Up.requireEnv
	}

	// Start to build the chain, but while building watch for:
	//   - divergent (split) chains
	//   - backRef's are valid (point to something)

	var head *AlterGroup
	var tail *AlterGroup

	for _, group := range groups {
		backRef := group.Up.backRef
		if backRef == "" {
			// could be a head-alter, skip
			continue
		}
		parent, ok := groups[backRef]
		if !ok {
			return nil, InvalidChainError(fmt.Sprintf("Invalid backref '%s' found for '%s'",
				backRef, group.Up.FileName))
		}

		// is always nil before set, impossible for previous loop to write this value
		group.BackRef = parent

		// If a forward-ref is not nil, then it has previously been established as a
		// parent alter. We have found a divergence in the chain.
		if parent.ForwardRef != nil {
			return nil, InvalidChainError(fmt.Sprintf(
				"Duplicate parent defined in %s and %s - both point to %s. Chain must be linear.",
				parent.ForwardRef.Up.ref,
				group.Up.ref,
				parent.Up.ref))
		}
		parent.ForwardRef = group
	}

	// Get head & tail from built chain and also make sure that no duplicate roots
	// are found. As for other potential errors:
	//   - abandoned alters
	//   - multiple tails (no next-refs)
	// These are already validated. Abandoned alters would have invalid refs,
	// duplicate parents, or be identified as a duplicate root. Tails would be
	// directed earlier as a divergent chain.
	for _, group := range groups {
		if group.BackRef == nil {
			if head != nil {
				return nil, InvalidChainError(fmt.Sprintf(
					"Duplicate root alters found (%s and %s). Chain must have one root alter.",
					group.Up.ref,
					head.Up.ref))
			}
			head = group
		}
		// Cannot have duplicate tail without already encountering another error
		if group.ForwardRef == nil {
			tail = group
		}
	}

	if head == nil || tail == nil {
		return nil, InvalidChainError("Chain is cyclic and has no head or tail")
	}

	chain := &Chain{
		Head: head,
		Tail: tail,
	}
	return chain, nil
}

// Scan a given directory and return a mapping of AlterRef to AlterGroup
// objects. The objects returned are un-validated aside from meta-data
// parsing.
func ScanDirectory(dir string) (map[string]*AlterGroup, error) {
	stat, err := os.Stat(dir)
	if err != nil {
		return nil, err
	}
	if !stat.IsDir() {
		return nil, errors.New(fmt.Sprintf("Path '%s' is not a directory", dir))
	}

	alters := make(map[string]*AlterGroup)
	files, err := ioutil.ReadDir(dir)
	for _, f := range files {
		if f.IsDir() {
			// only process top-level of dir
			continue
		}
		if isAlterFile(f.Name()) {
			filePath := path.Join(dir, f.Name())

			if header, err := readHeader(dir + "/" + f.Name()); err != nil {
				return nil, err
			} else {
				alter, err := parseMeta(header, filePath)
				if err != nil {
					return nil, err
				}
				group, ok := alters[alter.ref]
				if !ok {
					group = &AlterGroup{}
				}
				if alter.Direction == Up {
					if group.Up != nil {
						return nil, DuplicateRefError(
							fmt.Sprintf("Duplicate 'up' alter for ref '%s'", alter.ref))
					}
					group.Up = alter
				} else if alter.Direction == Down {
					if group.Down != nil {
						return nil, DuplicateRefError(
							fmt.Sprintf("Duplicate 'down' alter for ref '%s'", alter.ref))
					}
					group.Down = alter
				}
				alters[alter.ref] = group
			}
		}
	}

	if len(alters) == 0 {
		return nil, InvalidChainError(fmt.Sprintf(
			"Directory '%s' does not contain any alters", dir))
	}

	return alters, nil
}

// Check if the file is an "alter" by seeing if the name confirms to
// what we expect.
func isAlterFile(name string) bool {
	var filenameRegex = regexp.MustCompile(`^(\d+)-([^-]+-)+(up|down).sql$`)
	return filenameRegex.MatchString(name)
}

// Read the first N lines of an alter file that represent the "header." This is
// the bit of stuff that contains all the meta-data required in alters.
func readHeader(filePath string) ([]string, error) {
	var headerRegex = regexp.MustCompile(`^--`)
	lines := make([]string, 256)

	if file, err := os.Open(filePath); err != nil {
		return lines, err
	} else {
		// clone file after we return
		defer file.Close()

		// read line by line
		scanner := bufio.NewScanner(file)
		i := 0
		for scanner.Scan() {
			if i == 256 {
				return lines, InvalidMetaDataError(`Header lines (continuous block of lines starting with '--')
exceeds 256. Please add a blank line in-between the meta-data and any
comment lines that may follow.`)
			}
			line := scanner.Text()
			if headerRegex.MatchString(line) {
				lines[i] = line
				i++
			} else {
				// hit non-header line, we're done
				return lines, nil
			}
		}

		if err = scanner.Err(); err != nil {
			return lines, err
		}
	}

	return lines, nil
}

// Parse the meta-information from the file and return an Alter object.
// Returns error if meta cannot be obtained or required information is
// missing.
func parseMeta(lines []string, filePath string) (*Alter, error) {
	// expect meta-lines to be single-line and in the form of
	//   "-- key: value"
	// regex checks for extraneous whitespace
	var metaEntryRegex = regexp.MustCompile(`^--\s*([^\s]+)\s*:(.+)\s*$`)

	var alter = newDefaultAlter()
	alter.FileName = filePath

	for _, line := range lines {
		if matches := metaEntryRegex.FindStringSubmatch(line); len(matches) == 3 {
			// 3 matches means we're good to go
			key := strings.ToLower(strings.TrimSpace(matches[1]))
			value := strings.TrimSpace(matches[2])

			switch key {
			case "ref":
				if !isValidRef(value) {
					return nil, InvalidMetaDataError("Invalid 'ref' value found in " + filePath)
				}
				alter.ref = value
			case "backref":
				if value == "" {
					return nil, InvalidMetaDataError(fmt.Sprintf("Invalid 'backref' value found in '%s'", filePath))
				}
				alter.backRef = value
			case "direction":
				value_lower := strings.ToLower(value)
				if value_lower == "up" {
					alter.Direction = Up
				} else if value_lower == "down" {
					alter.Direction = Down
				} else {
					return nil, InvalidMetaDataError(fmt.Sprintf("Invalid direction '%s' found in '%s'", value_lower, filePath))
				}
			case "require-env":
				requiredEnvs := strings.Split(value, ",")
				for _, env := range requiredEnvs {
					trimmedStr := strings.TrimSpace(env)
					if trimmedStr != "" {
						alter.requireEnv = append(alter.requireEnv, trimmedStr)
					}
				}
			case "skip-env":
				skipEnvs := strings.Split(value, ",")
				for _, env := range skipEnvs {
					trimmedStr := strings.TrimSpace(env)
					if trimmedStr != "" {
						alter.skipEnv = append(alter.skipEnv, trimmedStr)
					}
				}
			default:
				log.Warn.Printf("Unknown property '%s' found in '%s'\n", key, filePath)
			}
		}
	}

	if alter.ref == "" {
		return nil, InvalidMetaDataError("Missing required field 'ref'")
	}
	// Note: backref isn't necessary here cause it could be the init file
	if alter.Direction == Undefined {
		return nil, InvalidMetaDataError("Missing required field 'direction'")
	}
	if len(alter.requireEnv) > 0 && len(alter.skipEnv) > 0 {
		return nil, InvalidMetaDataError("Mutually exclusive fields 'require-env' and 'skip-env' cannot be used together")
	}

	return alter, nil
}

// Validate that the ref is a valid identifier
func isValidRef(ref string) bool {
	var refRegex = regexp.MustCompile(`^[\da-zA-Z]+$`)
	return refRegex.MatchString(ref)
}
