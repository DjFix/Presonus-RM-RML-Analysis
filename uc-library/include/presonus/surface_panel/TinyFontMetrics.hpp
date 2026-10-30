#pragma once
#include <array>
#include <cstdint>
namespace presonus::surface_panel_port {
// Independent adapter to the genuine pinned CCL BitmapFont parser/metrics.
// Firmware glyph bytes remain separate data, not a source/license assertion.
const std::array<std::uint8_t, 475> &tinyFontBytes();
int tinyFontWidth(const char *text, int length);
} // namespace presonus::surface_panel_port
