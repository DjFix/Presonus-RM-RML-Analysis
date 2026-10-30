#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using namespace Presonus::Panel;
using Access = presonus::surface_panel_port::BitmapDrawingAccess;
struct Display final : BitmapDisplay {
  int height = 7;
  int getCharHeight() const override { return height; }
};
std::vector<unsigned char> decode(const std::string &text) {
  std::vector<unsigned char> out;
  if (text == "-")
    return out;
  for (std::size_t i = 0; i < text.size(); i += 2)
    out.push_back(
        static_cast<unsigned char>(std::stoul(text.substr(i, 2), nullptr, 16)));
  return out;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream file(argv[1]);
  assert(file);
  std::string mode, textHex, bitmapHex;
  int nullText, x, y, color, maximum, measure, fill, height, value,
      expectedColor, expectedX, expectedY, dirty;
  Rectangle expected{};
  unsigned cases = 0;
  while (file >> mode >> textHex >> nullText >> x >> y >> color >> maximum >>
         measure >> fill >> height >> value >> expectedColor >> expectedX >>
         expectedY >> dirty >> expected.x >> expected.y >> expected.width >>
         expected.height >> bitmapHex) {
    auto raw = decode(textHex);
    std::string text(raw.begin(), raw.end());
    Display display;
    display.height = height;
    Access::bitmap(display).fill(static_cast<unsigned char>(fill));
    Access::setState(display, 0, color, x, y);
    Access::dirty(
        display,
        false); // Explicit original oracle preseed, not constructor default.
    Rectangle box{11, 12, 13, 14};
    const char *input = nullText ? nullptr : text.c_str();
    if (mode == "height")
      assert(display.BitmapDisplay::getCharHeight() == value);
    else if (mode == "boxheight")
      assert(display.getTextBoxHeight() == value);
    else if (mode == "width")
      assert(display.pixelLength(input) == value);
    else if (mode == "draw")
      display.drawText(x, y, input, maximum, measure ? &box : nullptr);
    else
      display.drawString(input, maximum, measure ? &box : nullptr);
    auto state = Access::state(display);
    assert(state[1] == expectedColor && state[2] == expectedX &&
           state[3] == expectedY);
    if (Access::textDirty(display) != static_cast<bool>(dirty))
      std::cerr << "case " << cases << " " << mode << " x=" << x << " y=" << y
                << " bbox=" << measure << " expectedDirty=" << dirty
                << " actual=" << Access::textDirty(display) << "\n";
    assert(Access::textDirty(display) == static_cast<bool>(dirty));
    assert(box.x == expected.x && box.y == expected.y &&
           box.width == expected.width && box.height == expected.height);
    auto bitmap = decode(bitmapHex);
    assert(bitmap.size() == Access::bitmap(display).size());
    assert(std::equal(bitmap.begin(), bitmap.end(),
                      Access::bitmap(display).begin()));
    ++cases;
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
}
