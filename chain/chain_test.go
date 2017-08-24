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
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/appnexus/schema-tool/log"
)

//------------------------------------------------------------------------------
// ScanDirectory tests
//------------------------------------------------------------------------------
func TestScanNonExistantDir(t *testing.T) {
	if _, err := ScanDirectory("/dev/null/abcdefg"); err == nil {
		t.Fail()
	}
}

func TestScanNonDirFile(t *testing.T) {
	if _, err := ScanDirectory("/dev/null"); err == nil {
		t.Fail()
	}
}

func TestNormalSchemaDirs(t *testing.T) {
	dir, _ := os.Getwd()
	alterBaseDir := dir + "/../test/chains/"

	testData := []struct {
		dirName   string
		numAlters int
	}{
		{"normal-chain", 2},
		{"normal-embedded-invalid", 2},
		{"single-file-chain", 1},
	}

	for _, test := range testData {
		alterDir := alterBaseDir + test.dirName
		chain, err := ScanDirectory(alterDir)

		if err != nil {
			t.Log(err)
			t.Fail()
		}
		if len(chain) != test.numAlters {
			t.Logf("Length of chain was %d should have been %d", len(chain), test.numAlters)
			t.Fail()
		}
		for _, v := range chain {
			if v.Up == nil || v.Down == nil {
				t.Fail()
			}
		}
	}
}

func TestScanInvalidButValidForNowSchemas(t *testing.T) {
	// ScanDirectory returns us a "soft" chain that still needs to be validated.
	// This means that some chains may be invalid, but still successfully parsed
	// according to this function. That is what we're testing here.
	dir, _ := os.Getwd()
	alterBaseDir := dir + "/../test/chains/"

	testData := []struct {
		dirName   string
		numAlters int
	}{
		{"abandoned-alter", 3},
		{"circular-chain", 3},
		{"divergent-chain", 4},
		{"missing-down-alter", 2},
		{"missing-up-alter", 2},
		{"multiple-root", 3},
	}

	for _, test := range testData {
		alterDir := alterBaseDir + test.dirName
		chain, err := ScanDirectory(alterDir)

		if err != nil {
			t.Log(err)
			t.Fail()
		}
		if len(chain) != test.numAlters {
			t.Logf("Length of chain was %d should have been %d", len(chain), test.numAlters)
			t.Fail()
		}
	}
}

func TestScanInvalidSchemas(t *testing.T) {
	// Even though ScanDirectory does not do full-chain validtions, it can still
	// error on individually invalid alters (missing meta-data, etc).
	dir, _ := os.Getwd()
	alterBaseDir := dir + "/../test/chains/"

	testData := []struct {
		dirName string
		check   func(error) bool
	}{
		{
			"invalid-headers", func(e error) bool {
				_, ok := e.(InvalidMetaDataError)
				return ok
			},
		},
		{
			"duplicate-ref", func(e error) bool {
				_, ok := e.(DuplicateRefError)
				return ok
			},
		},
	}

	for _, test := range testData {
		alterDir := alterBaseDir + test.dirName
		_, err := ScanDirectory(alterDir)

		if err == nil {
			t.Logf("Should not consider chain '%s' valid. 'err' is nil", test.dirName)
			t.Fail()
		} else if !test.check(err) {
			t.Logf("Error does not satisfy check: '%s'", test.dirName)
			t.Fail()
		}
	}
}

// TODO: Test invalid meta-data
// TODO: Test duplicate ref (likely requires adding additional check in scan)

//------------------------------------------------------------------------------
// readHeader tests
//------------------------------------------------------------------------------
func TestReadHeaderNormalFile(t *testing.T) {
	dir, _ := os.Getwd()
	alter := dir + "/../test/chains/normal-chain/1234-init-up.sql"
	header, err := readHeader(alter)

	if err != nil {
		t.Fail()
	}

	// check that it stopped after reading first two lines
	if header[0] == "" || header[1] == "" {
		t.Fail()
	}
	if header[2] != "" {
		t.Fail()
	}
}

func TestReadHeaderNormalFileHeaderOnly(t *testing.T) {
	dir, _ := os.Getwd()
	alter := dir + "/../test/chains/normal-chain/1234-init-down.sql"
	header, err := readHeader(alter)

	if err != nil {
		t.Fail()
	}

	// check that it stopped after reading first two lines
	if header[0] == "" || header[1] == "" {
		t.Fail()
	}
	if header[2] != "" {
		t.Fail()
	}
}

func TestReaderHeaderNonExistantFile(t *testing.T) {
	dir, _ := os.Getwd()
	alter := dir + "/../test/chains/normal-chain/1234-dont-exist.up"
	if _, err := readHeader(alter); err == nil {
		t.Fail()
	}
}

func TestHeaderTooLarge(t *testing.T) {
	dir, _ := os.Getwd()
	alter := dir + "/../test/chains/invalid-headers/1234-init-up.sql"
	if _, err := readHeader(alter); err == nil {
		t.Fail()
	}
}

//------------------------------------------------------------------------------
// isAlterFile tests
//------------------------------------------------------------------------------
func TestAlterFilenameCheck(t *testing.T) {
	// positive assertions
	if !isAlterFile("1234-ABC-1234-some-update-up-down-blah-up.sql") {
		t.Fail()
	}
	if !isAlterFile("1234-ABC-1234-some-update-up-down-blah-down.sql") {
		t.Fail()
	}
	if !isAlterFile("1234-short-up.sql") {
		t.Fail()
	}
	if !isAlterFile("1234-i.has.dots-up.sql") {
		t.Fail()
	}

	// negative assertions
	if isAlterFile("1234-ABC-1234-some-uprade-up.sql.bak") {
		t.Fail()
	}
	if isAlterFile("ABC-1234-some-uprade-up.sql") {
		t.Fail()
	}
	if isAlterFile("1234-up.sql") {
		t.Fail()
	}
	if isAlterFile("1234-down.sql") {
		t.Fail()
	}
}

//------------------------------------------------------------------------------
// parseMeta tests
//------------------------------------------------------------------------------

func TestValidMetaData(t *testing.T) {
	var testData = []*struct {
		header  string
		isError bool
		alter   *Alter
	}{
		// valid entries (general)
		{"--ref: 1234abcd\n--direction: down", false, &Alter{ref: "1234abcd", direction: Down}},
		{"--ref: 1234abcd\n--direction: DOWN", false, &Alter{ref: "1234abcd", direction: Down}},
		{"--ref: 1234\n--backref:abcd\n--direction: down", false, &Alter{ref: "1234", backRef: "abcd", direction: Down}},
		// valid entries (test spacing)
		{"--ref: 1234\n--direction: up", false, &Alter{ref: "1234", direction: Up}},
		{"--ref:1234\n--direction:up", false, &Alter{ref: "1234", direction: Up}},
		{"-- ref: 1234\n-- direction: up", false, &Alter{ref: "1234", direction: Up}},
		{"-- ref:1234\n-- direction:up", false, &Alter{ref: "1234", direction: Up}},
		// valid entries (require-env)
		{"--ref:1234\n--direction:up\n--require-env: one", false,
			&Alter{ref: "1234", direction: Up, requireEnv: []string{"one"}}},
		{"--ref:1234\n--direction:up\n--require-env: one,", false,
			&Alter{ref: "1234", direction: Up, requireEnv: []string{"one"}}},
		{"--ref:1234\n--direction:up\n--require-env: one,,,", false,
			&Alter{ref: "1234", direction: Up, requireEnv: []string{"one"}}},
		{"--ref:1234\n--direction:up\n--require-env: one,two,three", false,
			&Alter{ref: "1234", direction: Up, requireEnv: []string{"one", "two", "three"}}},
		// valid entries (skip-env)
		{"--ref:1234\n--direction:up\n--skip-env: one", false,
			&Alter{ref: "1234", direction: Up, skipEnv: []string{"one"}}},
		{"--ref:1234\n--direction:up\n--skip-env: one,", false,
			&Alter{ref: "1234", direction: Up, skipEnv: []string{"one"}}},
		{"--ref:1234\n--direction:up\n--skip-env: one,,,", false,
			&Alter{ref: "1234", direction: Up, skipEnv: []string{"one"}}},
		{"--ref:1234\n--direction:up\n--skip-env: one,two,three", false,
			&Alter{ref: "1234", direction: Up, skipEnv: []string{"one", "two", "three"}}},
		// valid ignore unknown keys
		{"--ref: 1234\n--direction: up\n--boop:boop", false, &Alter{ref: "1234", direction: Up}},
		{"--ref: 1234\n--direction: up\n--reff:meow", false, &Alter{ref: "1234", direction: Up}},
		// ignore empty env keys
		{"--ref:1234\n--direction:up\n--require-env: ,,,", false, &Alter{ref: "1234", direction: Up}},
		{"--ref:1234\n--direction:up\n--require-env: ", false, &Alter{ref: "1234", direction: Up}},
		{"--ref:1234\n--direction:up\n--skip-env: ", false, &Alter{ref: "1234", direction: Up}},
		{"--ref:1234\n--direction:up\n--skip-env: ,,", false, &Alter{ref: "1234", direction: Up}},

		// invalid missing direction
		{"--ref: 1234\n--direction: sideways", true, nil},
		{"--ref: 1234\n--direction: upp", true, nil},
		{"--ref: 1234", true, nil},
		// invalid/missing refs
		{"--ref:1.2-4%", true, nil},
		{"--ref:1234\n--backref:1.2-4%", true, nil},
		{"--backref:1234\n", true, nil},
		//invalid require + skip envs
		{"--ref:1234\n--direction:up\n--skip-env: one\n--require-env:one", true, nil},
		{"--ref:1234\n--direction:up\n--skip-env: one\n--require-env:two", true, nil},
	}

	log.InitLoggers(false)
	for _, test := range testData {
		alter, err := parseMeta(strings.Split(test.header, "\n"), "./test")
		if err != nil && !test.isError {
			t.Fail()
		}
		if test.alter != nil && err == nil {
			if alter.ref != test.alter.ref {
				t.Fail()
			}
			if alter.backRef != test.alter.backRef {
				t.Fail()
			}
			if alter.direction != test.alter.direction {
				t.Fail()
			}
			if !equalStringSlices(alter.requireEnv, test.alter.requireEnv) {
				t.Fail()
			}
			if !equalStringSlices(alter.skipEnv, test.alter.skipEnv) {
				t.Fail()
			}
		}
	}
}

func equalStringSlices(a []string, b []string) bool {
	if len(a) != len(b) {
		fmt.Printf("%d -> %d\n", len(a), len(b))
		return false
	}
	for _, va := range a {
		found := false
		for _, vb := range b {
			if va == vb {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

//------------------------------------------------------------------------------
// isValidRef tests
//------------------------------------------------------------------------------

func TestIsValidRef(t *testing.T) {
	var testData = []*struct {
		ref   string
		valid bool
	}{
		{ref: "hello", valid: true},
		{ref: "1234567890", valid: true},
		{ref: "1234abc", valid: true},
		{ref: "abc1234def", valid: true},
		{ref: "", valid: false},
		{ref: " 1234 ", valid: false},
	}

	for _, test := range testData {
		if isValidRef(test.ref) != test.valid {
			if test.valid {
				fmt.Printf("Failed to accept valid ref: '%s'\n", test.ref)
			}
			t.Fail()
		}
	}
}
