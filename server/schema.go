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
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/appnexus/schema-tool/lib/chain"

	"github.com/appnexus/schema-tool/lib/log"
	"github.com/gorilla/mux"
	uuid "github.com/satori/go.uuid"
)

// createSchema is the JSON representation used to add a schema via the
// `newSchemaHandler`
type createSchema struct {
	Dir   string `json:"directory"`
	Empty bool   `json:"empty"`
}

// createdSchema is the JSON representation to return the ID of the created schema
type createdSchema struct {
	ID string `json:"id"`
}

// schema represents the internal representation of how schemas are stored by the
// schema portion of the server
type schema struct {
	ID    string `json:"id"`
	Dir   string `json:"directory"`
	Empty bool   `json:"empty"`
}

var schemas = make(map[string]schema, 128)

// newSchemaHandler accepts a `createSchema` struct and scans the directory on the
// host the server is running on and creates an in-memory representation of the
// schema. This is then stored in-memory and an ID is returned to identify the
// schema for future operations.
//
// If the directory is not found, or the contents of the directory are not found
// to be a valid schema chain, then a 400 error response will be returned.
func (s *httpServer) newSchemaHandler(w http.ResponseWriter, r *http.Request) {
	create := &createSchema{}
	err := json.NewDecoder(r.Body).Decode(create)
	if err != nil {
		WriteErrorResponse(w, NewUserError(MalformedRequest, "Could not parse request body into expected JSON"))
		return
	}

	if create.Empty {
		// generate ID and store empty schema
		s := schema{
			ID:    uuid.NewV4().String(),
			Dir:   create.Dir,
			Empty: true,
		}
		schemas[s.ID] = s

		// write ID back to HTTP response
		createJSON := createdSchema{ID: s.ID}
		w.Header().Add("Content-Type", "application/json")
		err := json.NewEncoder(w).Encode(createJSON)
		if err != nil {
			log.Error.Printf("Unexpected error while encoding JSON response: %v\n", err)
		}
		return
	}

	// check if directory exists & scan directory and build local representation
	_, err = chain.ScanDirectory(create.Dir)
	if err != nil {
		// wrap up the error and return it to the user
		return
	}
	// generate ID and store schema
	// return ID
}

// getSchemaByIDHandler returns a single schema object or a 404 response error if it cannot
// be found.
func (s *httpServer) getSchemaByIDHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	if id, ok := vars["id"]; ok {
		if schema, ok := schemas[id]; ok {
			w.Header().Add("Content-Type", "application/json")
			err := json.NewEncoder(w).Encode(schema)
			if err != nil {
				log.Error.Printf("Unexpected error while encoding JSON response: %v\n", err)
			}
			return
		}
		WriteErrorResponse(w, NewUserError(NotFound, fmt.Sprintf("schema with id '%s' was not found", id)))
		return
	}

	WriteErrorResponse(w, NewUserError(MalformedRequest, "No ID specified to retrieve"))
}

// getAllSchemasHandler dumps all known schemas back to the user. This handler should never return
// anything but a successful response, even if just returning an empty array.
func (s *httpServer) getAllSchemasHandler(w http.ResponseWriter, r *http.Request) {
	schemaList := make([]schema, len(schemas))
	for _, schema := range schemas {
		schemaList = append(schemaList, schema)
	}
	w.Header().Add("Content-Type", "application/json")
	err := json.NewEncoder(w).Encode(schemaList)
	if err != nil {
		log.Error.Printf("Unexpected error while encoding JSON response: %v\n", err)
	}
}

// deleteSchemaHandler deletes a schema from the internal store. Note however that this
// doesn't take any action on the underlying filesystem.
func (s *httpServer) deleteSchemaHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	if id, ok := vars["id"]; ok {
		if _, ok := schemas[id]; ok {
			delete(schemas, id)
			w.WriteHeader(http.StatusOK)
			return
		}
		WriteErrorResponse(w, NewUserError(NotFound, fmt.Sprintf("schema with id '%s' was not found", id)))
		return
	}
	WriteErrorResponse(w, NewUserError(MalformedRequest, "No ID specified to retrieve"))
}
