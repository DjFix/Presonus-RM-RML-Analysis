#include "presonus/panel/Element.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  if (!input)
    return 3;
  std::string method;
  long long argument;
  unsigned int expected;
  unsigned int cases = 0;
  while (input >> method >> argument >> expected) {
    Presonus::Panel::Element element;
    std::array<unsigned char, sizeof(element)> before{};
    std::memcpy(before.data(), &element, sizeof(element));
    unsigned int actual;
    if (method == "deltaEncoder")
      actual = element.deltaEncoder(static_cast<int>(argument));
    else if (method == "tap")
      actual = element.tap();
    else if (method == "next")
      actual = element.next();
    else if (method == "getParam")
      actual = element.getParam();
    else if (method == "previous")
      actual = element.previous();
    else
      return 4;
    if (actual != expected ||
        std::memcmp(before.data(), &element, sizeof(element)) != 0)
      return 5;
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 6;
  std::cout << "Element portable replay passed " << cases
            << " independent native fixture cases; object bytes unchanged\n";
}
