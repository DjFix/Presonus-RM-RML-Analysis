#include "presonus/mixer_dsp/EQControl.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  Presonus::EQControl control(presonus::dsp::EQControlBiquadPortTag{});
  int index, expected;
  unsigned count = 0;
  while (input >> index >> expected) {
    assert(index >= 0);
    assert(control.getBiquadType(index) == expected);
    ++count;
  }
  assert(input.eof() && count > 1000);
  std::cout << count << " exact cases\n";
}
