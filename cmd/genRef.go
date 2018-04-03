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

// genRefCmd represents the genRef command
var genRefCmd = &cobra.Command{
	Use:   "gen-ref",
	Short: "Generate a new file-ref",
	Long: `
Generate a reference that could be used for an alter file.

This is a utility command, to give the user flexibility in
how new alter files are created. It is not necessary for in
the normal workflow. Normal being defined as the workflow
presented in this project's documentation.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("genRef called")
	},
}

func init() {
	RootCmd.AddCommand(genRefCmd)
}
