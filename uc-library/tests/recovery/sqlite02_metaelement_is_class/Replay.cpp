#include "presonus/uc/meta_element.hpp"

#include <iostream>
#include <string_view>

int main(int argc, char **argv) {
  if (argc != 3)
    return 1;
  const auto input = [](const char *arg) {
    return std::string_view(arg) == "<null>" ? nullptr : arg;
  };
  const Presonus::UC::MetaElement element(input(argv[1]), nullptr);
  std::cout << element.isClass(input(argv[2])) << '\n';
}
