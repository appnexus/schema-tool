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

var filenameNew string

// newCmd represents the new command
var newCmd = &cobra.Command{
	Use:   "new",
	Short: "Create a new alter",
	Long: `
Create a new alter in the chain. Two files will be created for an
'up' and 'down' alter. The current alter chain must be valid
(verified by the 'check' command) as the newly created alter will
be added to the end of the chain.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("new called")
	},
}

func init() {
	RootCmd.AddCommand(newCmd)

	newCmd.PersistentFlags().StringVarP(&filenameNew, "file", "f", "",
		"The name of the new file (without file-extension)")
}
