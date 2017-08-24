package cmd

import (
	"github.com/spf13/viper"

	"github.com/appnexus/schema-tool/log"
	"github.com/appnexus/schema-tool/server"
	"github.com/spf13/cobra"
)

var serverCmd = &cobra.Command{
	Use:   "server",
	Short: "Start/Stop/Manage the schema server.",
	Long: `
Manages a HTTP server to manage schemas and projects. The HTTP
Server exposes all of the functionality used by other commands
to impliment their functionality. Thus, the server is the ideal
way to interact and extend the schema tool from a programmatic
perspective.`,
}

var startServerCmd = &cobra.Command{
	Use:   "start",
	Short: "Start the schema server",
	Long: `
Start the HTTP server. Note that this command blocks and does
not fork or call some other process to start the server. Sending
a SIGQUIT or SIGINT signal to the process will result in a
graceful shutdown of the server.

See the help docs of the top-level "server" command for more
details on what the schema server does.`,
	Run: func(cmd *cobra.Command, args []string) {
		log.Info.Println("Initializing schema server...")
		serverConfig := retrieveServerConfig()

		err := server.Start(serverConfig)
		if err != nil {
			log.Warn.Println(err)
		}
	},
}

// retrieveServerConfig creates a server.Config object from the global
// Viper confiuration "store"
func retrieveServerConfig() *server.Config {
	log.Info.Println("Validating server configuration...")
	return &server.Config{
		Port: viper.GetInt("server.port"),
	}
}

func init() {
	// Set default server configuration values
	viper.SetDefault("server.port", -1)

	// Register all commands
	serverCmd.AddCommand(startServerCmd)
	RootCmd.AddCommand(serverCmd)
}
