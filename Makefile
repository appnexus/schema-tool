BUILD_OPTS=-p 4 -race
BIN_NAME=schema

default: test

travis: compile
	@echo
	@echo "[running tests] (with codecov.io-compat cover report)"
	@bash script/multi-cover.sh

test: compile
	@echo
	@echo "[running tests]"
	@go test github.com/appnexus/schema-tool... -cover

compile: copyright
	go build $(BUILD_OPTS) -o $(BIN_NAME)
	go vet
	golint .
	@gotags -tag-relative=true -R=true -sort=true -f="tags" -fields=+l .

release: copyright
	@mkdir -p release-binaries/
	# Linux
	env GOOS=linux GOARCH=amd64 go build $(BUILD_OPTS) -o release-binaries/$(BIN_NAME)_linux_amd64
	env GOOS=linux GOARCH=386 go build $(BUILD_OPTS) -o release-binaries/$(BIN_NAME)_linux_386
	# Mac OS
	env GOOS=darwin GOARCH=amd64 go build $(BUILD_OPTS) -o release-binaries/$(BIN_NAME)_darwin_amd64
	env GOOS=darwin GOARCH=386 go build $(BUILD_OPTS) -o release-binaries/$(BIN_NAME)_darwin_386
	# Windows
	env GOOS=windows GOARCH=amd64 go build $(BUILD_OPTS) -o release-binaries/$(BIN_NAME)_win_amd64
	env GOOS=windows GOARCH=386 go build $(BUILD_OPTS) -o release-binaries/$(BIN_NAME)_win_386

copyright:
	@echo "Applying copyright to all Go source files"
	@./script/copyright-header.sh

setup:
	go get -u github.com/tools/godep
	go get -u github.com/golang/lint/golint
	go get -u github.com/jstemmer/gotags
	godep restore
	npm install -g doctoc

doctoc:
	doctoc readme.md --github
