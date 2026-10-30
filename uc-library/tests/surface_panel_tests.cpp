#include "presonus/surface_panel/ControlHelpers.hpp"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

void require(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}
std::string unhex(const std::string &text) {
  if (text == "-")
    return {};
  require(text.size() % 2 == 0, "bad string fixture");
  std::string out;
  for (std::size_t i = 0; i < text.size(); i += 2)
    out.push_back(
        static_cast<char>(std::stoul(text.substr(i, 2), nullptr, 16)));
  return out;
}
int main(int argc, char **argv) {
  try {
    require(argc == 2, "ARM fixture path required");
    std::ifstream input(argv[1]);
    require(bool(input), "cannot read ARM fixture");
    Presonus::Panel::SevenSegControl display;
    Presonus::Surface::PanelRegistrar registrar;
    Presonus::Surface::SurfaceRootComponent root;
    unsigned seven = 0, groups = 0, names = 0;
    char operation;
    while (input >> operation) {
      if (operation == 'S') {
        std::string role;
        unsigned character, dot, expected;
        require(bool(input >> role >> character >> dot >> expected),
                "bad segment fixture");
        require(display.convertCharToBmp(static_cast<char>(character),
                                         dot != 0) == expected,
                "seven-segment mismatch for " + role + ":" +
                    std::to_string(character));
        ++seven;
      } else if (operation == 'G') {
        int group, expected;
        require(bool(input >> group >> expected), "bad group fixture");
        require(registrar.mapGroupIdToControlType(
                    static_cast<Presonus::Panel::ControlRegistrar::ControlType>(
                        group)) == expected,
                "group mismatch " + std::to_string(group));
        ++groups;
      } else {
        require(operation == 'T', "unknown fixture");
        int isNull, expected;
        std::string text;
        require(bool(input >> isNull >> text >> expected),
                "bad transport fixture");
        auto name = unhex(text);
        require(root.isTransportControl(isNull ? nullptr : name.c_str()) ==
                    bool(expected),
                "transport-name mismatch " + text);
        ++names;
      }
    }
    require(seven == 1024 && groups > 65536 && names > 3000,
            "missing expected domain coverage");
    std::cout << "PASS: " << seven << " seven-segment, " << groups
              << " control-group, " << names
              << " transport-name ARM differential fixtures\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
