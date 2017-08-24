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

var forceInit bool

// initCmd represents the init command
var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize a new project",
	Long: `
Initialize a new project including installing any pre-commit hook
defined in the config (if any) and setting up a history table in the
DB for revision tracking.
`,
	Run: func(cmd *cobra.Command, args []string) {

		// TODO: determine DB type we want to use (params or global configs)
		// TODO: generate a project config (if needed) (interactively prompt for any needed values)
		// TODO: create an initial blank alter
		fmt.Println("init called")
	},
}

func init() {
	RootCmd.AddCommand(initCmd)

	initCmd.PersistentFlags().BoolVarP(&forceInit, "force", "f", false,
		"forcibly initialize the history table (wiping all old data)")
}
