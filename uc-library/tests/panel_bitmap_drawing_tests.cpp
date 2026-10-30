#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>

using Presonus::Panel::BitmapDisplay;
using Presonus::Panel::Rectangle;
using presonus::surface_panel_port::BitmapDrawingAccess;
using Frame = std::array<std::uint8_t, 3072>;
static Frame initialFrame(std::uint32_t seed) {
  Frame frame{};
  for (auto &byte : frame) {
    seed = seed * 1664525U + 1013904223U;
    byte = static_cast<std::uint8_t>(seed >> 24U);
  }
  return frame;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::unordered_map<std::uint32_t, Frame> cache;
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    char operation;
    unsigned role, alias, changes;
    std::uint32_t seed, expectedReturn, expectedX, expectedY;
    std::array<std::uint32_t, 4> before{}, after{};
    std::array<std::uint32_t, 5> args{};
    if (!(row >> operation >> role >> seed))
      return 3;
    for (auto &value : before)
      row >> value;
    for (auto &value : args)
      row >> value;
    row >> alias >> expectedReturn;
    for (auto &value : after)
      row >> value;
    row >> expectedX >> expectedY >> changes;
    auto found = cache.find(seed);
    if (found == cache.end())
      found = cache.emplace(seed, initialFrame(seed)).first;
    Frame expected = found->second;
    for (unsigned i = 0; i < changes; ++i) {
      unsigned offset, value;
      row >> offset >> value;
      if (offset >= expected.size() || value > 255)
        return 4;
      expected[offset] = static_cast<std::uint8_t>(value);
    }
    if (!row)
      return 5;
    BitmapDisplay display;
    BitmapDrawingAccess::bitmap(display) = found->second;
    BitmapDrawingAccess::setState(display, static_cast<std::int32_t>(before[0]),
                                  static_cast<std::int32_t>(before[1]),
                                  static_cast<std::int32_t>(before[2]),
                                  static_cast<std::int32_t>(before[3]));
    const auto a = static_cast<std::int32_t>(args[0]);
    const auto b = static_cast<std::int32_t>(args[1]);
    const auto c = static_cast<std::int32_t>(args[2]);
    const auto d = static_cast<std::int32_t>(args[3]);
    const auto e = static_cast<std::int32_t>(args[4]);
    const Rectangle rectangle{a, b, c, d};
    std::uint32_t result = 0;
    int outX = 0x01234567;
    int outY = static_cast<std::int32_t>(0x89abcdefU);
    switch (operation) {
    case 'W':
      result = display.getScreenWidth();
      break;
    case 'H':
      result = display.getScreenHeight();
      break;
    case 'G':
      result = display.getPixel(a, b);
      break;
    case 'P':
      display.setPixel(a, b, c != 0);
      break;
    case 'F':
      display._fillRect(a, b, c, d, e);
      break;
    case 'R':
      display._fillRect(rectangle, e);
      break;
    case 'A':
      display.fillRect(rectangle);
      break;
    case 'E':
      display.eraseRect(rectangle);
      break;
    case 'I':
      display.invertRect(rectangle);
      break;
    case 'L':
      result = static_cast<std::uint32_t>(display.setPen(a));
      break;
    case 'T':
      result = static_cast<std::uint32_t>(display.setTextColor(a));
      break;
    case 'M':
      display.moveTo(a, b);
      break;
    case 'O':
      display.getPos(outX, alias ? outX : outY);
      break;
    default:
      return 6;
    }
    const auto state = BitmapDrawingAccess::state(display);
    bool stateEqual = true;
    for (unsigned i = 0; i < state.size(); ++i)
      stateEqual =
          stateEqual && static_cast<std::uint32_t>(state[i]) == after[i];
    if (result != expectedReturn || !stateEqual ||
        static_cast<std::uint32_t>(outX) != expectedX ||
        static_cast<std::uint32_t>(outY) != expectedY ||
        BitmapDrawingAccess::bitmap(display) != expected) {
      std::fprintf(stderr, "Mismatch case %u op %c role %u return %u/%u\n",
                   cases, operation, role, result, expectedReturn);
      return 1;
    }
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 7;
  std::printf("PASS: %u original ARM BitmapDisplay differential cases\n",
              cases);
}
