#include "presonus/panel/Page.hpp"

#include <cstring>
#include <string>
#include <utility>

using Presonus::Panel::Page;

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string name(argv[1]);
  std::string input(name);
  const Page left({}, input);
  const Page right({}, std::move(input));
  input.assign("unrelated input");
  const char *leftName = left.getName();
  const char *rightName = right.getName();
  return leftName == rightName || leftName != left.getName() ||
         rightName != right.getName() || std::strcmp(leftName, name.c_str()) ||
         std::strcmp(rightName, name.c_str()) || *Page().getName() != '\0';
}
