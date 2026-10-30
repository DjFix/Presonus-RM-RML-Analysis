#include "presonus/surface_panel/TinyFontMetrics.hpp"
#include "core/portable/gui/corefont.h"
#include "core/public/corememstream.h"
#include <stdexcept>
#include <vector>
namespace presonus::surface_panel_port {
namespace {
void word(std::vector<std::uint8_t> &out, unsigned value, int bytes) {
  for (int i = 0; i < bytes; ++i)
    out.push_back(static_cast<std::uint8_t>(value >> (8 * i)));
}
std::vector<std::uint8_t> descriptor() {
  std::vector<std::uint8_t> out{'B', 'M', 'F', 3};
  out.push_back(2);
  word(out, 15, 4);
  for (unsigned value : {7U, 7U, 1U, 1U, 1U})
    word(out, value, 2);
  for (int i = 0; i < 5; ++i)
    out.push_back(0);
  out.push_back(4);
  word(out, 95 * 20, 4);
  const auto &glyphs = tinyFontBytes();
  for (unsigned code = 32; code <= 126; ++code) {
    unsigned width = 0;
    for (unsigned column = 0; column < 5; ++column)
      width += glyphs[(code - 32) * 5 + column] != 251;
    word(out, code, 4);
    word(out, 0, 2);
    word(out, 0, 2);
    word(out, width, 2);
    word(out, 7, 2);
    word(out, 0, 2);
    word(out, 0, 2);
    word(out, width + 1, 2);
    out.push_back(0);
    out.push_back(0);
  }
  return out;
}
struct Metrics {
  Core::Portable::Bitmap bitmap;
  Core::Portable::BitmapFont font{"firmware-fontmid", &bitmap, false};
  Metrics() {
    auto bytes = descriptor();
    Core::IO::MemoryStream stream(bytes.data(),
                                  static_cast<Core::uint32>(bytes.size()));
    if (!font.loadDescriptor(stream))
      throw std::runtime_error("valid generated BMFont required");
  }
};
} // namespace
int tinyFontWidth(const char *text, int length) {
  static Metrics metrics;
  return metrics.font.getStringWidth(text, length);
}
} // namespace presonus::surface_panel_port
