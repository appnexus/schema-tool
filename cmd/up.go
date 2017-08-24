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

package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var numberUp int
var forceUp bool
var noUndoUp bool

// upCmd represents the up command
var upCmd = &cobra.Command{
	Use:   "up [REF]",
	Short: "Bring up the schema to a specified revision",
	Long: `
Bring up the schema to a specified version by running
the 'up' alters, starting from the one after the last
applied alter. The history table is used to determine
the current state of the database and is altered during
the roll forward.

Args:
  REF   Run all alters up to, and including, the REF given`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("up called")
	},
}

func init() {
	RootCmd.AddCommand(upCmd)

	upCmd.PersistentFlags().IntVarP(&numberUp, "number", "n", 0,
		"Number of up-alters from current state. overrides args")
	upCmd.PersistentFlags().BoolVarP(&forceUp, "force", "f", false,
		"Continue running up-alters even if an error has occurred")
	upCmd.PersistentFlags().BoolVarP(&noUndoUp, "no-undo", "u", false,
		"When comparing histories do not undo any previously ran alters")
}
