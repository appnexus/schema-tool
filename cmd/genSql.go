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

var noRevisionGenSQL bool
var noSQLGenSQL bool
var downGenSQL bool
var includeRevisionAlterGenSQL bool
var writeToFileGenSQL bool

// genSqlCmd represents the genSql command
var genSQLCmd = &cobra.Command{
	Use:   "gen-sql",
	Short: "Generate SQL for a specified reference (includes revision-history alter)",
	Long: `
Generate SQL files which includes alters to the revision-history
tables (as configured for this repo) that can be applied manually
without the use of this tool.

See the docs for a full discussion on why gen-sql is useful.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("genSql called")
	},
}

func init() {
	RootCmd.AddCommand(genSQLCmd)

	// Here you will define your flags and configuration settings.

	genSQLCmd.PersistentFlags().BoolVarP(&noRevisionGenSQL, "no-revision", "R", false,
		"Do not print out the revision-history alter statements")
	genSQLCmd.PersistentFlags().BoolVarP(&noSQLGenSQL, "no-sql", "S", false,
		"Do not generate SQL for the actual alters, just revision inserts")
	genSQLCmd.PersistentFlags().BoolVarP(&downGenSQL, "down", "D", false,
		"Generate SQL for down-alter instead of up (default)")
	genSQLCmd.PersistentFlags().BoolVarP(&includeRevisionAlterGenSQL, "include-rev-query", "q", false,
		"Include the revision query in the generated sql")
	genSQLCmd.PersistentFlags().BoolVarP(&writeToFileGenSQL, "write-to-file", "w", false,
		"Do not print to STDOUT. Instead, write SQL to file in 'static_alter_dir' directory specified in config.")
	// Cobra supports Persistent Flags which will work for this command
	// and all subcommands, e.g.:
	// genSQLCmd.PersistentFlags().String("foo", "", "A help for foo")

	// Cobra supports local flags which will only run when this command
	// is called directly, e.g.:
	// genSQLCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}
