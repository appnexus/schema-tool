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
	"os"
	"path"
	"strings"

	"github.com/appnexus/schema-tool/log"
	homedir "github.com/mitchellh/go-homedir"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var cfgFileGlobal string
var cwDirGlobal string
var verboseGlobal bool

// RootCmd represents the base command when called without any subcommands
var RootCmd = &cobra.Command{
	Use:   "schema-tool",
	Short: "Manage your schemas with ease",
	Long: `
A tool for managing schemas by basing alters around an alter-chain which
is an ordering of how alters are applied to a given environment. Managing
alters within a chain allows the tool to incrementally setup and tear
down a database; the enforced ordering grants us reliable execution across
multiple environments.

The goal of the tool is to be both a local tool for setting up and tearing
down dev environments as well as a tool for applying changes to production
environments. All changes are tracked through the revision-history table
for auditing purposes.`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	if err := RootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig, initLoggers)

	cwd, err := os.Getwd()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	// Peristent flags available to all sub-commands
	// global config
	RootCmd.PersistentFlags().StringVar(
		&cfgFileGlobal,
		"config",
		"",
		"config file (default is $HOME/.schema-tool.toml)")

	// directory we're running in
	RootCmd.PersistentFlags().StringVarP(
		&cwDirGlobal,
		"dir",
		"d",
		cwd,
		"directory to run schema commands in (default is current dir)")

	// verbose output/logging
	RootCmd.PersistentFlags().BoolVarP(
		&verboseGlobal,
		"verbose",
		"v",
		false,
		"verbose output")
}

// initConfig configures the Viper library on how to load configuration values
// for the schema-tool. This uses a combination of environment variables and
// config files to obtain values. Actual configuration values are not loaded by
// the application here, but obtained as needed with `viper.Get()`.
func initConfig() {
	if cfgFileGlobal != "" {
		// Use config file from user-defined input
		viper.SetConfigFile(cfgFileGlobal)
	} else {
		// Find home directory.
		home, err := homedir.Dir()
		if err != nil {
			fmt.Println("Error locating default config file." +
				"Could not resolve home directory for current user.")
			fmt.Println(err)
			os.Exit(1)
		}

		// Setup all search directories
		viper.AddConfigPath(home)
		viper.AddConfigPath(path.Join(home, ".config"))
		viper.AddConfigPath("/etc/")
		viper.SetConfigName(".schema-tool")
	}

	// Setup viper to read config overrides from the ENV variables
	viper.SetEnvPrefix("schema")
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	viper.AutomaticEnv()

	// If a config file is found, read it in.
	if err := viper.ReadInConfig(); err == nil {
		fmt.Println("Using config file:", viper.ConfigFileUsed())
	}
}

func initLoggers() {
	log.InitLoggers(verboseGlobal)
}
