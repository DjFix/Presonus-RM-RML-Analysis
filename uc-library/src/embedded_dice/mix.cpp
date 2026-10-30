#include "presonus/embedded_dice/mix.hpp"
#include <iomanip>
#include <locale>
#include <sstream>

namespace presonus::embedded_dice {
namespace {
constexpr std::uint32_t config = 0xc4000200U;
constexpr std::uint32_t gain_register = 0xc4000204U;
constexpr std::uint32_t overflow = 0xc400020cU;
constexpr std::uint32_t bad_parameter = 0xc3000003U;
constexpr const char *source =
    "/media/psf/Home/Presonus/svn/tcat/trunk/firmware/project/sdk/packages/"
    "dice/dice_audio/current/src/diceMixer.c";
std::uint32_t reject(MixIo &io, std::uint32_t line) {
  io.diagnostic(bad_parameter, line, source);
  return bad_parameter;
}
} // namespace

std::uint32_t mix_clrin(MixIo &io, std::uint32_t input) {
  if (input > 31U)
    return reject(io, 120);
  for (std::uint32_t output = 0; output < 32; ++output)
    io.write32(gain_register, (input << 22) | (output << 27));
  return 0;
}
std::uint32_t mix_clrout(MixIo &io, std::uint32_t output) {
  if (output > 31U)
    return reject(io, 101);
  for (std::uint32_t input = 0; input < 32; ++input)
    io.write32(gain_register, (output << 27) | (input << 22));
  return 0;
}
std::uint32_t mix_gain(MixIo &io, std::uint32_t output, std::uint32_t input,
                       std::uint32_t gain) {
  if (output > 31U || input > 31U)
    return reject(io, 84);
  io.write32(gain_register, (output << 27) | (input << 22) | (gain & 0xffffU));
  return 0;
}
std::uint32_t mix_cfg(MixIo &io, std::uint32_t inputs, std::uint32_t outputs,
                      std::uint32_t enabled) {
  if (inputs > 32U || outputs > 32U)
    return reject(io, 62);
  if (inputs == 0 || outputs == 0 || enabled == 0)
    io.write32(config, 0);
  else
    io.write32(config, ((inputs - 1) << 24) | ((outputs - 1) << 16) | 3U);
  for (std::uint32_t input = 0; input < 32; ++input)
    mix_clrin(io, input);
  return 0;
}
std::uint32_t mix_dump(MixIo &io) {
  const auto value = io.read32(config);
  io.write32(config, value);
  io.print("Mixer\r\n");
  if ((value & 1U) == 0) {
    io.print("  Disabled\r\n");
    return 0;
  }
  io.print("  ins=" + std::to_string(((value >> 24) & 31U) + 1) +
           ", outs=" + std::to_string(((value >> 16) & 31U) + 1) + "\r\n");
  io.print(std::string("  error : ") +
           ((value & 2U) ? "PROC. OVERFLOW" : "None") + "\r\n");
  std::ostringstream line;
  line.imbue(std::locale::classic());
  line << "  ofl   : " << std::hex << std::setfill('0') << std::setw(8)
       << io.read32(overflow) << "\r\n";
  io.print(line.str());
  io.print("DCP not implemented for mixer dump!\r\n");
  io.print("\r\n");
  return 0;
}
} // namespace presonus::embedded_dice
