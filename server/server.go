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

package server

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/appnexus/schema-tool/lib/log"
	"github.com/gorilla/mux"
	"github.com/pkg/errors"
)

// Config is the main configuration struct for starting a new server
type Config struct {
	Port int
}

// httpServer is an instance of the web-server containing all stateful data
// needed by the handlers.
type httpServer struct {
	config *Config
	port   int
}

// Start starts an HTTP server. This server does not return until the
// server is stopped, which is realistically until the process is killed
// or an interrupt signal is received.
func Start(c *Config) error {
	server := &httpServer{
		config: c,
	}
	r := mux.NewRouter()
	r.HandleFunc("/schema", server.newSchemaHandler).Methods("POST")
	r.HandleFunc("/schema", server.getAllSchemasHandler).Methods("GET")
	r.HandleFunc("/schema/{id}", server.getSchemaByIDHandler).Methods("GET")
	r.HandleFunc("/schema/{id}", server.deleteSchemaHandler).Methods("DELETE")

	if c.Port <= 0 {
		port, err := getFreePort()
		if err != nil {
			return errors.Wrap(err, "Could not obtain a free port for server to listen on")
		}
		c.Port = port
	}
	h := &http.Server{Addr: fmt.Sprintf(":%d", c.Port), Handler: r}
	var serverErr error
	go func() {
		serverErr = h.ListenAndServe()
	}()
	log.Info.Printf("Starting server at 0.0.0.0:%d\n", c.Port)

	// setup graceful shutdown via signal handlers
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGTERM, syscall.SIGINT)

	<-stop
	ctx := context.Background()
	h.Shutdown(ctx)
	if serverErr != nil {
		log.Info.Println(serverErr)
	}
	log.Info.Println("Shuting down http server...")
	return nil
}

// getFreePort finds a free TCP port that can be used to start-up a web server
// on. If an error is returned, then a 0-value is given for the port and should
// not be used to bind on.
func getFreePort() (int, error) {
	addr, err := net.ResolveTCPAddr("tcp", "localhost:0")
	if err != nil {
		return 0, err
	}

	l, err := net.ListenTCP("tcp", addr)
	if err != nil {
		return 0, err
	}
	defer l.Close()
	log.Info.Printf("Located available port: %d\n", l.Addr().(*net.TCPAddr).Port)
	return l.Addr().(*net.TCPAddr).Port, nil
}
