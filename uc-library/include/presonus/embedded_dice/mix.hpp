#pragma once
#include <cstdint>
#include <string>

// Independent portable semantic port. Names are CLI registration labels;
// original C/C++ identifiers, scopes and calling ABI remain unresolved.
namespace presonus::embedded_dice {
class MixIo {
public:
  virtual ~MixIo() = default;
  virtual std::uint32_t read32(std::uint32_t address) = 0;
  virtual void write32(std::uint32_t address, std::uint32_t value) = 0;
  virtual void diagnostic(std::uint32_t code, std::uint32_t line,
                          const char *file) = 0;
  // One call per observed firmware printf call, after formatting.
  virtual void print(const std::string &text) = 0;
};
std::uint32_t mix_clrin(MixIo &, std::uint32_t input);
std::uint32_t mix_clrout(MixIo &, std::uint32_t output);
std::uint32_t mix_gain(MixIo &, std::uint32_t output, std::uint32_t input,
                       std::uint32_t gain);
std::uint32_t mix_cfg(MixIo &, std::uint32_t inputs, std::uint32_t outputs,
                      std::uint32_t enabled);
std::uint32_t mix_dump(MixIo &);
} // namespace presonus::embedded_dice
