.PHONY: all clean
all:
ifeq ($(GATES),yes)
	python3 run_tests.py --netlist gate_level_netlist.v
else
	python3 run_tests.py
endif
clean:
	@echo "Prior evidence retained; every run uses a fresh output directory."
