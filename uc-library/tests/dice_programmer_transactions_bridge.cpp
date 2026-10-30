#include "presonus/dice/programmer.hpp"
#include <array>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <linux/spi/spidev.h>
#include <sstream>
#include <string>
#include <vector>

namespace {
void require(bool condition) {
  if (!condition)
    std::abort();
}
std::vector<unsigned char> unhex(const std::string &text) {
  if (text == "-")
    return {};
  std::vector<unsigned char> result;
  for (std::size_t i = 0; i < text.size(); i += 2)
    result.push_back(std::stoul(text.substr(i, 2), nullptr, 16));
  return result;
}
std::string hex(const unsigned char *data, std::size_t count) {
  std::ostringstream output;
  for (std::size_t i = 0; i < count; ++i)
    output << std::hex << std::setfill('0') << std::setw(2)
           << unsigned(data[i]);
  return output.str();
}
std::int32_t signedWord(std::uint32_t word) {
  std::int32_t result;
  std::memcpy(&result, &word, 4);
  return result;
}
class Recorder final : public presonus::dice::ProgrammerServices {
public:
  std::int32_t descriptor = 0;
  std::vector<std::uint32_t> results;
  std::vector<std::vector<unsigned char>> replies;
  std::vector<std::int64_t> ticks;
  std::vector<std::string> events;
  unsigned transfers = 0, clocks = 0;
  std::int32_t
  transfer(std::int32_t fd,
           const presonus::dice::ProgrammerTransfer &transfer) override {
    require(fd == descriptor && transfers < replies.size());
    const std::uint32_t total =
        transfer.transmitLength + transfer.receiveLength;
    require(total == replies[transfers].size());
    std::ostringstream event;
    event << "{\"kind\":\"transfer\",\"txlen\":" << transfer.transmitLength
          << ",\"rxlen\":" << transfer.receiveLength << ",\"total\":" << total
          << ",\"command_prefix\":\""
          << hex(transfer.transmit, transfer.transmitLength)
          << "\",\"speed\":1000000,\"bits\":8,\"delay\":0,\"cs\":0}";
    events.push_back(event.str());
    if (total)
      std::memcpy(transfer.receive, replies[transfers].data(), total);
    return signedWord(results[transfers++]);
  }
  std::int64_t clockRawTicks() override {
    require(clocks < ticks.size());
    const auto value = ticks[clocks++];
    events.push_back("{\"kind\":\"clock\",\"ticks\":" + std::to_string(value) +
                     "}");
    return value;
  }
  void sleepMilliseconds(std::uint32_t value) override {
    require(value == 1);
    events.push_back("{\"kind\":\"sleep\",\"milliseconds\":1}");
  }
};
bool ioctlExpected = false;
unsigned ioctlCount = 0;
} // namespace

extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  require(ioctlExpected && fd == -7 && request == SPI_IOC_MESSAGE(1));
  va_list args;
  va_start(args, request);
  auto *transfer = va_arg(args, spi_ioc_transfer *);
  va_end(args);
  require(transfer->len == 4 && transfer->speed_hz == 1000000 &&
          transfer->bits_per_word == 8 && transfer->delay_usecs == 0 &&
          transfer->cs_change == 0);
  const auto *tx = reinterpret_cast<const unsigned char *>(transfer->tx_buf);
  require(tx[0] == 0x9f && tx[1] == 0 && tx[2] == 0 && tx[3] == 0);
  auto *rx = reinterpret_cast<unsigned char *>(transfer->rx_buf);
  rx[0] = 0;
  rx[1] = 0x20;
  rx[2] = 0x80;
  rx[3] = 0x17;
  ++ioctlCount;
  return 4;
}

int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider-smoke") {
    presonus::dice::LinuxProgrammerTransport transport;
    presonus::dice::CclProgrammerServices services(transport);
    const auto before = services.clockRawTicks();
    services.sleepMilliseconds(1);
    require(services.clockRawTicks() >= before);
    Presonus::DICE::Dice3Programmer programmer(nullptr, nullptr, 0);
    programmer.bindProgrammerServices(services, -7);
    ioctlExpected = true;
    require(programmer.readJedecId() == 0x8017 && ioctlCount == 1);
    ioctlExpected = false;
    std::cout << "PASS actual CCL clock/sleep/buffer and Linux SPI "
                 "translation; ioctl intercepted, no devices\n";
    return 0;
  }
  require(argc == 1);
  unsigned kind;
  while (std::cin >> kind) {
    std::uint32_t descriptor, txlen, rxlen;
    int timeout;
    unsigned count;
    std::string txHex;
    std::cin >> descriptor >> timeout >> txlen >> rxlen >> txHex >> count;
    Recorder recorder;
    recorder.descriptor = signedWord(descriptor);
    for (unsigned i = 0; i < count; ++i) {
      std::uint32_t result;
      std::string reply;
      std::cin >> result >> reply;
      recorder.results.push_back(result);
      recorder.replies.push_back(unhex(reply));
    }
    std::cin >> count;
    for (unsigned i = 0; i < count; ++i) {
      std::int64_t ticks;
      std::cin >> ticks;
      recorder.ticks.push_back(ticks);
    }
    require(bool(std::cin));
    const auto tx = unhex(txHex);
    require(tx.size() == txlen);
    std::array<unsigned char, 64> rx{};
    Presonus::DICE::Dice3Programmer programmer(nullptr, nullptr, 0);
    programmer.bindProgrammerServices(recorder, recorder.descriptor);
    const auto before = programmer.inspectState();
    std::int32_t result;
    switch (kind) {
    case 0:
      result =
          programmer.performTransaction({tx.data(), txlen, rx.data(), rxlen});
      break;
    case 1:
      result = programmer.writeEnable();
      break;
    case 2:
      result = programmer.readJedecId();
      break;
    default:
      require(kind == 3);
      result = programmer.busyWait(timeout);
      break;
    }
    const auto after = programmer.inspectState();
    require(before.descriptor == after.descriptor &&
            before.image == after.image && before.length == after.length &&
            before.listener == after.listener);
    std::cout << "{\"return_word\":" << static_cast<std::uint32_t>(result)
              << ",\"events\":[";
    for (unsigned i = 0; i < recorder.events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << recorder.events[i];
    }
    std::cout << ']';
    if (kind == 0)
      std::cout << ",\"received\":\"" << hex(rx.data(), txlen + rxlen) << '"';
    std::cout << "}\n";
  }
  require(std::cin.eof());
}
