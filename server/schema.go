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
	"net/http"
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

	// check if directory exists
	// scan directory and build local representation
	// store in store and generate ID
	// return ID
}
