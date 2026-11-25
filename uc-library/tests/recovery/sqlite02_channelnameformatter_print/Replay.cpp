#include "presonus/uc/ChannelNameFormatter.hpp"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>

using Presonus::UC::Format::ChannelNameFormatter;

namespace {
struct Derived final : ChannelNameFormatter {};

#if CHANNEL_FORMATTER_CASE == 2 || CHANNEL_FORMATTER_CASE == 3
const void *receiver;
bool armed;
int receiverDeletes;

void observeDelete(const void *pointer) {
  if (!armed)
    return;
  if (pointer != receiver || receiverDeletes != 0)
    std::abort();
  ++receiverDeletes;
}
#endif

#if CHANNEL_FORMATTER_CASE == 3
[[gnu::noipa]] void destroy(Core::Formatter *value) { delete value; }
#endif

void printHex(const std::array<unsigned char, 36> &bytes) {
  constexpr char digits[] = "0123456789abcdef";
  for (auto byte : bytes)
    std::cout << digits[byte >> 4] << digits[byte & 15];
  std::cout << '\n';
}
} // namespace

#if CHANNEL_FORMATTER_CASE == 2 || CHANNEL_FORMATTER_CASE == 3
extern "C" void __real__ZdlPv(void *pointer);
extern "C" void __wrap__ZdlPv(void *pointer) {
  observeDelete(pointer);
  __real__ZdlPv(pointer);
}
extern "C" void __real__ZdlPvm(void *pointer, std::size_t size);
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  observeDelete(pointer);
  __real__ZdlPvm(pointer, size);
}
#endif

int main() {
#if CHANNEL_FORMATTER_CASE == 0 || CHANNEL_FORMATTER_CASE == 1
#if CHANNEL_FORMATTER_CASE == 0
  static ChannelNameFormatter value;
#else
  static Derived value;
#endif
  Core::FormatterRegistry::add(&value);
  const auto *bound = Core::FormatterRegistry::find(value.getName());
  if (bound != &value)
    return 1;
  char output[8]{};
  Core::Formatter::Data data{nullptr, output, sizeof(output), 0.f, nullptr};
  bound->print(data);
  if (std::strcmp(output, "Off") != 0)
    return 1;
  std::cout << bound->getName() << '\n';
#elif CHANNEL_FORMATTER_CASE == 2 || CHANNEL_FORMATTER_CASE == 3
#if CHANNEL_FORMATTER_CASE == 2
  alignas(
      ChannelNameFormatter) unsigned char storage[sizeof(ChannelNameFormatter)];
  auto *value = new (storage) ChannelNameFormatter;
#else
  auto *value = new ChannelNameFormatter;
#endif
  const auto *borrowed = value->getName();
  receiver = value;
  armed = true;
#if CHANNEL_FORMATTER_CASE == 2
  value->~ChannelNameFormatter();
#else
  destroy(value);
#endif
  armed = false;
  if (std::strcmp(borrowed, "ch_name") != 0)
    return 1;
  std::cout << receiverDeletes << '\n';
#elif CHANNEL_FORMATTER_CASE == 4
  struct Input {
    std::uint32_t bits;
    int capacity;
    bool hasBuffer;
  };
  constexpr Input inputs[] = {
      {0x00000000, 32, true}, {0x80000000, 4, true},  {0, 2, true},
      {0, 1, true},           {0, 0, true},           {0, 8, false},
      {0x41480000, 32, true}, {0xc0600000, 32, true}, {0x3f000000, 32, true},
      {0x42c80000, 5, true},  {0xc3a10000, 3, true},  {0xcf000000, 32, true},
      {0x4effffff, 32, true}, {0x3f800000, 0, true},  {0xbf800000, 8, false},
  };
  ChannelNameFormatter value;
  for (const Input &input : inputs) {
    float number;
    std::memcpy(&number, &input.bits, sizeof(number));
    std::array<unsigned char, 36> output;
    output.fill(0xa5);
    char *buffer =
        input.hasBuffer ? reinterpret_cast<char *>(output.data()) : nullptr;
    Core::Formatter::Data data{nullptr, buffer, input.capacity, number,
                               nullptr};
    value.print(data);
    std::uint32_t observed;
    std::memcpy(&observed, &data.value, sizeof(observed));
    if (observed != input.bits || data.string != buffer ||
        data.size != input.capacity || data.object || data.range)
      return 1;
    printHex(output);
  }
#else
#error "Select a ChannelNameFormatter replay case"
#endif
}
