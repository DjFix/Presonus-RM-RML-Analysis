#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using Access = presonus::surface_panel_port::BitmapDrawingAccess;
static std::vector<char> decode(const std::string &s) {
  std::vector<char> b;
  for (unsigned i = 0; i < s.size(); i += 2)
    b.push_back(static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return b;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  std::string mode, a, b, c, oa, ob, oc;
  int alias, own, pen, dirty;
  Presonus::Panel::Point point;
  Presonus::Panel::Rectangle rect;
  unsigned cases = 0;
  while (in >> mode >> point.x >> point.y >> rect.x >> rect.y >> rect.width >>
         rect.height >> alias >> own >> pen >> dirty >> a >> b >> c >> oa >>
         ob >> oc) {
    Presonus::Panel::BitmapDisplay display;
    auto i0 = decode(a), source = decode(b), destination = decode(c),
         e0 = decode(oa), e1 = decode(ob), e2 = decode(oc);
    auto &bitmap = Access::bitmap(display);
    std::copy(i0.begin(), i0.end(), bitmap.begin());
    Access::setState(display, pen, 0, 0, 0);
    Access::dirty(
        display,
        false); // Explicit original oracle preseed, not constructor default.
    char *dst = own ? display.getBitmapData() : destination.data();
    const char *src = alias ? dst : source.data();
    if (mode == "raw")
      display.copyBits(dst, src, point, rect);
    else if (mode == "copy")
      display.copyBits(src, point, rect);
    else if (mode == "get")
      display.getScreenBits(dst, point, rect);
    else if (mode == "clear")
      display.clear();
    else if (display.getBitmapData() != reinterpret_cast<char *>(bitmap.data()))
      throw std::runtime_error("getter identity");
    if (!std::equal(bitmap.begin(), bitmap.end(), e0.begin(),
                    [](unsigned char a, char b) {
                      return a == static_cast<unsigned char>(b);
                    }) ||
        source != e1 || destination != e2 ||
        Access::textDirty(display) != bool(dirty))
      throw std::runtime_error("copy/clear bytes or dirty differ case" +
                               std::to_string(cases));
    ++cases;
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
}
