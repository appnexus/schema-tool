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

	"github.com/appnexus/schema-tool/lib/log"
)

// ErrorMsg is the generic error JSON response that is sent back anytime an
// error is encountered while interacting with the API
type ErrorMsg struct {
	ErrorCode string `json:"error_code"`
	ErrorType string `json:"error_type"`
	ErrorMsg  string `json:"error_message"`
}

// NewUserError returns an error object given the code and message with an error-type
// of `ErrorTypeUser`
func NewUserError(code string, message string) *ErrorMsg {
	return &ErrorMsg{
		ErrorCode: code,
		ErrorType: ErrorTypeUser,
		ErrorMsg:  message,
	}
}

// NewSystemError returns an error object given the code and message with an error-type
// of `ErrorTypeSystem`
func NewSystemError(code string, message string) *ErrorMsg {
	return &ErrorMsg{
		ErrorCode: code,
		ErrorType: ErrorTypeSystem,
		ErrorMsg:  message,
	}
}

// WriteErrorResponse encodes a given error message and writes to an HTTP response
// object, setting appropriate headers.
func WriteErrorResponse(w http.ResponseWriter, e *ErrorMsg) {
	w.Header().Add("Content-Type", "application/json")
	if e.ErrorType == ErrorTypeUser {
		WriteErrorResponseWithStatus(w, e, http.StatusBadRequest)
	} else {
		WriteErrorResponseWithStatus(w, e, http.StatusInternalServerError)
	}
}

// WriteErrorResponseWithStatus is a utility function to respond with errors using a
// custom status code not dependent upon the ErrorType
func WriteErrorResponseWithStatus(w http.ResponseWriter, e *ErrorMsg, status int) {
	w.Header().Add("Content-Type", "application/json")
	w.WriteHeader(status)
	err := json.NewEncoder(w).Encode(e)
	if err != nil {
		log.Error.Printf("Unexpected error while encoding JSON response: %v\n", err)
	}
}

const (
	// ErrorTypeUser is an error-type to signify that it is the fault of the user
	// (the one providing input to the server)
	ErrorTypeUser = "USER"

	// ErrorTypeSystem is an error-type to signify that something unexpected happened
	// and is not an error resulting from invalid user input. This type of error
	// could be due to misconfiguration of the schema-tooling, system, or indicate the
	// precense of a bug.
	ErrorTypeSystem = "SYSTEM"
)

const (
	// InvalidDirectory is an error when adding a new schema with a directory
	// that does not exist or cannot be read.
	InvalidDirectory = "INVALID_DIRECTORY"

	// InvalidSchema is an error when adding a new schema with an invalid chain
	InvalidSchema = "INVALID_SCHEMA"

	// MalformedRequest is an error for when the user provides a request that is not
	// formatted correctly (i.e. It does not deserialize into the expected JSON request
	// body)
	MalformedRequest = "MALFORMED_REQUEST"

	// NotFound is an error returned for when any object being looked up is not found
	NotFound = "NOT_FOUND"
)
