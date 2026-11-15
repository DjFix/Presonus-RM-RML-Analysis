#include "presonus/mixer/ControlMapping.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
int main() {
  unsigned count = 0;
  for (auto input : {std::string(), std::string("gain"), std::string(31, 'x'),
                     std::string(32, 'x'), std::string(80, 'x')}) {
    for (std::uintptr_t p : {std::uintptr_t(0), std::uintptr_t(0x200800)}) {
      auto *parameter = reinterpret_cast<Core::Portable::Parameter *>(p);
      Core::CString32 provider(input.c_str());
      Presonus::Mixer::ControlMapping actual(parameter, input.c_str());
      assert(actual.parameter() == parameter);
      assert(std::strcmp(actual.name(), provider.str()) == 0);
      ++count;
    }
    {
      Core::CString32 provider(nullptr);
      Presonus::Mixer::ControlMapping actual(nullptr, nullptr);
      assert(std::strcmp(actual.name(), provider.str()) == 0);
      ++count;
    }
  }
  std::cout << count << " provider comparisons passed\n";
}
