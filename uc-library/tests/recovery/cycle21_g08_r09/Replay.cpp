#include "presonus/utilities/dfu_diagnostic.hpp"
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int value = std::stoi(argv[1]);
  const char *first = getDFUErr(value);
  const std::string saved(first);
  for (int code = 1999; code <= 2010; ++code)
    (void)getDFUErr(code);
  if (saved != first || first != getDFUErr(value))
    return 3;
  std::cout << saved << '\n';
}
