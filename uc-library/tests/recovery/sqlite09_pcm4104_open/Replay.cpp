#include "presonus/pcm4104/Pcm4104Spi.hpp"

#include <array>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <linux/spi/spidev.h>
#include <new>
#include <string_view>
#include <type_traits>

#if defined(PCM4104_PREDECESSOR_REPLAY)
// Earlier borrowed and disconnected entries should never acquire or close a
// descriptor. Trap either operation if the implementation regresses.
extern "C" int __wrap_open(const char *, int, ...) { std::abort(); }
extern "C" int __wrap_close(int) { std::abort(); }
#else

using Pcm = Presonus::PCM4104::Pcm4104Spi;

extern "C" void
constructComplete(Pcm *,
                  const char *) asm("_ZN8Presonus7PCM410410Pcm4104SpiC1EPKc");
extern "C" void
constructBase(Pcm *,
              const char *) asm("_ZN8Presonus7PCM410410Pcm4104SpiC2EPKc");
extern "C" void
destroyComplete(Pcm *) asm("_ZN8Presonus7PCM410410Pcm4104SpiD1Ev");
extern "C" void destroyBase(Pcm *) asm("_ZN8Presonus7PCM410410Pcm4104SpiD2Ev");

extern "C" int *__real___errno_location() noexcept;
extern "C" void __real__ZN4Core11DebugPrintfEPKcz(const char *, ...);

namespace {
constexpr const char *path = "pcm4104-offline";
bool observe;
int openResult;
int failingStep;
unsigned ioctlCount;
unsigned modeValue;
unsigned responseValue;
unsigned closes;
const unsigned char *observedObject;
} // namespace

extern "C" int *__wrap___errno_location() noexcept {
  if (observe)
    std::cout << "errno\n";
  return __real___errno_location();
}

extern "C" int __wrap_open(const char *name, int flags, ...) {
  if (observe) {
    int fd;
    std::memcpy(&fd, observedObject, sizeof fd);
    std::cout << "open " << name << ' ' << flags << ' ' << fd;
    for (unsigned offset = sizeof fd; offset < sizeof fd + 4; ++offset)
      std::cout << ' ' << unsigned(observedObject[offset]);
    std::cout << '\n';
  }
  if (openResult < 0)
    *__real___errno_location() = 9;
  return openResult;
}

extern "C" int __wrap_close(int descriptor) {
  ++closes;
  if (observe)
    std::cout << "close " << descriptor << '\n';
  if (failingStep == 1) {
    *__real___errno_location() = 5;
    return -1;
  }
  return 0;
}

extern "C" int __wrap_ioctl(int descriptor, unsigned long request, ...) {
  va_list args;
  va_start(args, request);
  if (request == SPI_IOC_RD_MODE || request == SPI_IOC_WR_MODE) {
    auto *mode = va_arg(args, std::uint8_t *);
    if (observe)
      std::cout << "mode " << descriptor << ' ' << request << ' '
                << unsigned(*mode) << '\n';
    if (request == SPI_IOC_RD_MODE)
      *mode = static_cast<std::uint8_t>(modeValue);
  } else {
    auto *transfer = va_arg(args, spi_ioc_transfer *);
    if (request != SPI_IOC_MESSAGE(1) || transfer->len != 2 ||
        !transfer->tx_buf || !transfer->rx_buf ||
        transfer->tx_buf == transfer->rx_buf || transfer->rx_nbits ||
        transfer->tx_nbits || transfer->word_delay_usecs || transfer->pad)
      std::abort();
    const auto *tx = reinterpret_cast<const unsigned char *>(transfer->tx_buf);
    auto *rx = reinterpret_cast<unsigned char *>(transfer->rx_buf);
    if (observe)
      std::cout << "transfer " << descriptor << ' ' << request << ' '
                << transfer->len << ' ' << transfer->speed_hz << ' '
                << transfer->delay_usecs << ' '
                << unsigned(transfer->bits_per_word) << ' '
                << unsigned(transfer->cs_change) << ' ' << unsigned(tx[0])
                << ' ' << unsigned(tx[1]) << '\n';
    rx[0] = static_cast<unsigned char>(responseValue ^ 0xff);
    rx[1] = static_cast<unsigned char>(responseValue);
  }
  va_end(args);
  if (++ioctlCount == static_cast<unsigned>(failingStep)) {
    *__real___errno_location() = 5;
    return -1;
  }
  return 0;
}

extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  if (observe)
    std::cout << "diagnostic ";
  if (std::string_view(format) == "SPI: Failed to open PCM4104 SPI port\n") {
    __real__ZN4Core11DebugPrintfEPKcz(format);
  } else {
    const std::string_view formatView(format);
    if (formatView != "SPI error on transfer: %d\n" &&
        formatView != "SPI: error reading mode %d\n" &&
        formatView != "SPI error writing mode %d\n")
      std::abort();
    va_list args;
    va_start(args, format);
    const int value = va_arg(args, int);
    va_end(args);
    __real__ZN4Core11DebugPrintfEPKcz(format, value);
  }
}

int main(int argc, char **argv) {
  static_assert(std::is_standard_layout_v<Pcm> && sizeof(int) == 4);
  if (argc != 2)
    return 2;
  const std::string_view method(argv[1]);
  if (method == "borrowed") {
    closes = 0;
    {
      [[maybe_unused]] auto receiver = Pcm::withBorrowedSpiDescriptor(17);
    }
    return closes ? 3 : 0;
  }
  int initial, opened, failure, channel, value;
  std::uint32_t gainBits;
  unsigned modeByte, response;
  while (std::cin >> initial >> opened >> failure >> channel >> value >>
         gainBits >> modeByte >> response) {
    alignas(Pcm) std::array<unsigned char, sizeof(Pcm)> storage{};
    Pcm *receiver = reinterpret_cast<Pcm *>(storage.data());
    bool alive = true;
    const bool constructing =
        method == "base_construct" || method == "complete_construct";
    if (!constructing) {
      if ((method == "open" ||
           (method == "base_destroy" || method == "complete_destroy")) &&
          initial) {
        openResult = initial;
        failingStep = 0;
        ioctlCount = 0;
        receiver = new (storage.data()) Pcm(path);
      } else {
        receiver =
            new (storage.data()) Pcm(Pcm::withBorrowedSpiDescriptor(initial));
      }
    }
    observedObject = storage.data();
    openResult = opened;
    failingStep = failure;
    ioctlCount = 0;
    modeValue = modeByte;
    responseValue = response;
    *__real___errno_location() = 71;
    observe = true;
    int result = -1;
    if (method == "base_construct") {
      constructBase(receiver, path);
    } else if (method == "complete_construct") {
      constructComplete(receiver, path);
    } else if (method == "base_destroy") {
      destroyBase(receiver);
      alive = false;
    } else if (method == "complete_destroy") {
      destroyComplete(receiver);
      alive = false;
    } else if (method == "open") {
      result = receiver->open(path);
    } else if (method == "configure_defaults") {
      result = receiver->configureDefaults();
    } else if (method == "mute_channel") {
      result = receiver->muteChannel(channel, value != 0);
    } else if (method == "set_attenuation_value") {
      result = receiver->setAttenuationValue(channel, value);
    } else if (method == "attenuate_channel") {
      float gain;
      std::memcpy(&gain, &gainBits, sizeof gain);
      result = receiver->attenuateChannel(channel, gain);
    } else {
      return 2;
    }
    observe = false;
    int fd;
    std::memcpy(&fd, storage.data(), sizeof fd);
    std::cout << "state " << result << ' ' << fd;
    for (unsigned offset = sizeof fd; offset < sizeof fd + 4; ++offset)
      std::cout << ' ' << unsigned(storage[offset]);
    std::cout << ' ' << *__real___errno_location() << '\n';
    if (alive)
      receiver->~Pcm();
  }
  return std::cin.eof() ? 0 : 4;
}

#endif
