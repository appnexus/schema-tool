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

var forceDown bool
var numDown int

// downCmd represents the down command
var downCmd = &cobra.Command{
	Use:   "down [base|all|REF]",
	Short: "Roll back the schema to a specified version",
	Long: `
Roll back the schema to a specified version by running
the 'down' alters, starting from the last applied alter.
The history table is used to determine the current state
of the database and is altered during the rollback.

Args:
  all    Undo all alters
  base   Undo all but the initial alter
  REF    Undo all previously run alters up to, and including, the ref given`,
	PreRunE: func(cmd *cobra.Command, args []string) error {
		return nil
	},
	Run: func(cmd *cobra.Command, args []string) {
		// parse args for one of [base|all|REF]
		fmt.Println("down called")
	},
}

func init() {
	RootCmd.AddCommand(downCmd)

	// Peristent flags available to all sub-commands
	downCmd.PersistentFlags().BoolVarP(&forceDown, "force", "f", false,
		"continue applying alters if error is encountered")
	downCmd.PersistentFlags().IntVarP(&numDown, "number", "n", 0,
		"number of down alters to run from current state. overrides args")
}
