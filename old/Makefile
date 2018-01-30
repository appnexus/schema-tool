default: doctoc

setup:
	npm install -g doctoc

doctoc:
	doctoc readme.md --github
	cp readme.md README
	doctoc README --github
