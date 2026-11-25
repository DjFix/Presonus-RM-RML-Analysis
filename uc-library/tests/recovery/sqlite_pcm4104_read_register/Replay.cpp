#include "presonus/pcm4104/Pcm4104Spi.hpp"

#include <array>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <linux/spi/spidev.h>
#include <string_view>

namespace {
struct Trace {
  unsigned descriptor;
  unsigned long request;
  unsigned length;
  unsigned speed;
  unsigned delay;
  unsigned bits;
  unsigned csChange;
  unsigned tx0;
  unsigned tx1;
};

Trace trace;
unsigned calls;
int result;
int injectedErrno;
int response;
unsigned errnoReads;
unsigned diagnosticCalls;
bool monitorErrno;
} // namespace

extern "C" int *__real___errno_location() noexcept;

extern "C" int *__wrap___errno_location() noexcept {
  if (monitorErrno) {
    if (calls != 1)
      std::abort();
    ++errnoReads;
  }
  return __real___errno_location();
}

extern "C" void __real__ZN4Core11DebugPrintfEPKcz(const char *format, ...);

extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  if (!monitorErrno || calls != 1 || errnoReads != 1 ||
      ++diagnosticCalls != 1 ||
      std::string_view(format) != "SPI error on transfer: %d\n")
    std::abort();

  va_list args;
  va_start(args, format);
  const int error = va_arg(args, int);
  va_end(args);
  if (error != injectedErrno)
    std::abort();

  __real__ZN4Core11DebugPrintfEPKcz(format, error);
}

extern "C" int __wrap_ioctl(int descriptor, unsigned long request, ...) {
  va_list args;
  va_start(args, request);
  const auto *transfer = va_arg(args, spi_ioc_transfer *);
  va_end(args);
  if (++calls != 1 || transfer->len != 2 || !transfer->tx_buf ||
      !transfer->rx_buf || transfer->tx_buf == transfer->rx_buf ||
      transfer->rx_nbits || transfer->tx_nbits || transfer->word_delay_usecs ||
      transfer->pad)
    std::abort();

  const auto *tx = reinterpret_cast<const unsigned char *>(transfer->tx_buf);
  auto *rx = reinterpret_cast<unsigned char *>(transfer->rx_buf);
  trace = {static_cast<unsigned>(descriptor),
           request,
           transfer->len,
           transfer->speed_hz,
           transfer->delay_usecs,
           transfer->bits_per_word,
           transfer->cs_change,
           tx[0],
           tx[1]};
  if (response >= 0) {
    rx[0] = static_cast<unsigned char>(response ^ 0xff);
    rx[1] = static_cast<unsigned char>(response);
  }
  if (result < 0)
    *__real___errno_location() = injectedErrno;
  return result;
}

int main(int argc, char **argv) {
  using Presonus::PCM4104::Pcm4104Spi;
  if (argc != 2)
    return 2;
  const std::string_view mode(argv[1]);
  if (mode != "read" && mode != "write")
    return 2;
  int descriptor, index, value;
  unsigned count = 0;
  while (std::cin >> descriptor >> index >> value >> result >> injectedErrno >>
         response) {
    auto receiver = descriptor
                        ? Pcm4104Spi::withBorrowedSpiDescriptor(descriptor)
                        : Pcm4104Spi{};
    std::array<unsigned char, sizeof(receiver)> originalState;
    std::memcpy(originalState.data(), &receiver, originalState.size());
    unsigned char output[] = {0x75, static_cast<unsigned char>(value), 0x8e};
    calls = 0;
    errnoReads = 0;
    diagnosticCalls = 0;
    *__real___errno_location() = 33;
    monitorErrno = true;
    const bool success = mode == "read"
                             ? receiver.readRegister(index, output + 1)
                             : receiver.writeRegister(index, output[1]);
    monitorErrno = false;
    const int observedErrno = *__real___errno_location();
    if (std::memcmp(originalState.data(), &receiver, originalState.size()) ||
        output[0] != 0x75 || output[2] != 0x8e)
      return 3;
    std::cout << success << ' ' << unsigned(output[1]) << ' ' << observedErrno
              << ' ' << errnoReads << ' ' << diagnosticCalls;
    if (calls)
      std::cout << ' ' << trace.descriptor << ' ' << trace.request << ' '
                << trace.length << ' ' << trace.speed << ' ' << trace.delay
                << ' ' << trace.bits << ' ' << trace.csChange << ' '
                << trace.tx0 << ' ' << trace.tx1;
    std::cout << '\n';
    ++count;
  }
  return std::cin.eof() && count ? 0 : 4;
}
