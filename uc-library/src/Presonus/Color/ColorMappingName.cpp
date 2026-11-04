#include "presonus/reconstruction200/large01_w06.hpp"
#include <array>
#include <cstring>
namespace Presonus {
Core::Color ColorMapping::mapColor(const char *name) {
  // Same exact logical palette as the existing native-initializer-backed
  // ColorMapping provider; no repeat nearest-color reconstruction.
  struct NamedColor {
    const char *name;
    Core::Color color;
  };
  static const std::array<NamedColor, 17> palette{
      {{"red", {255, 0, 0, 255}},
       {"orange", {252, 167, 19, 255}},
       {"lightorange", {252, 201, 64, 255}},
       {"pink", {254, 213, 229, 255}},
       {"pinkish", {255, 226, 147, 255}},
       {"yellow", {255, 255, 0, 255}},
       {"coral", {83, 189, 77, 255}},
       {"blueishwhite", {179, 253, 253, 255}},
       {"white", {240, 240, 240, 255}},
       {"purple", {250, 104, 250, 255}},
       {"deeppurple", {153, 97, 246, 255}},
       {"green", {0, 255, 0, 255}},
       {"powderblue", {128, 234, 234, 255}},
       {"turquoise", {2, 237, 201, 255}},
       {"lightblue", {79, 211, 255, 255}},
       {"blue", {0, 0, 255, 255}},
       {"off", {0, 0, 0, 255}}}};
  const char *safeName = name ? name : "";
  for (const auto &item : palette)
    if (std::strcmp(safeName, item.name) == 0)
      return item.color;
  return Core::Color(0, 0, 0, 0);
}
} // namespace Presonus
