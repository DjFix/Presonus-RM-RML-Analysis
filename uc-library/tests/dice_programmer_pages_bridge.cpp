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
unsigned char *sharedReceive = nullptr;
const unsigned char *sharedTransmit = nullptr;
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
    if (!sharedReceive)
      sharedReceive = transfer.receive;
    require(sharedReceive == transfer.receive &&
            transfer.transmit != transfer.receive);
    if (transfer.transmitLength >= 4) {
      if (!sharedTransmit)
        sharedTransmit = transfer.transmit;
      require(sharedTransmit == transfer.transmit &&
              sharedTransmit != sharedReceive);
    }

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
const unsigned char providerCommands[] = {5, 6, 2, 5, 3, 3};
} // namespace
extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  require(ioctlExpected && fd == -7 && request == SPI_IOC_MESSAGE(1));
  va_list args;
  va_start(args, request);
  auto *transfer = va_arg(args, spi_ioc_transfer *);
  va_end(args);
  const auto *tx = reinterpret_cast<const unsigned char *>(transfer->tx_buf);
  auto *rx = reinterpret_cast<unsigned char *>(transfer->rx_buf);
  require(ioctlCount < sizeof(providerCommands) &&
          tx[0] == providerCommands[ioctlCount]);
  require(transfer->speed_hz == 1000000 && transfer->bits_per_word == 8 &&
          transfer->delay_usecs == 0 && transfer->cs_change == 0);
  if (tx[0] == 5) {
    require(transfer->len == 2 && tx[1] == 0);
  } else if (tx[0] == 6) {
    require(transfer->len == 1);
  } else {
    require(transfer->len == 260);
    if (ioctlCount == 5)
      require(tx[1] == 0x56 && tx[2] == 0x78 && tx[3] == 0);
    else
      require(tx[1] == 0xff && tx[2] == 0xff && tx[3] == 0);
    for (unsigned i = 4; i < 260; ++i)
      require(tx[i] == (tx[0] == 2 ? 0xff : 0));
  }
  std::memset(rx, 0, transfer->len);
  ++ioctlCount;
  return transfer->len;
}
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider-smoke") {
    presonus::dice::LinuxProgrammerTransport transport;
    presonus::dice::CclProgrammerServices services(transport);
    Presonus::DICE::Dice3Programmer programmer(nullptr, nullptr, 0);
    programmer.bindProgrammerServices(services, -7);
    ioctlExpected = true;
    require(programmer.writePage(-1, nullptr, -7) == 0);
    std::array<unsigned char, 256> zeros{};
    require(programmer.verifyPage(-1, zeros.data(), 256) == 0);
    require(programmer.dumpPage(0x12345678) == 0);
    require(ioctlCount == 6);
    ioctlExpected = false;
    std::cout << "PASS actual CCL clocks/buffers and six full Linux page SPI "
                 "translations; ioctl intercepted, no devices\n";
    return 0;
  }
  require(argc == 1);
  unsigned kind;
  while (std::cin >> kind) {
    std::uint32_t descriptor, pageWord, lengthWord;
    unsigned count;
    std::string dataHex;
    std::cin >> descriptor >> pageWord >> lengthWord >> dataHex >> count;
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
    const auto data = unhex(dataHex);
    require(data.size() == 256);
    Presonus::DICE::Dice3Programmer programmer(nullptr, nullptr, 0);
    programmer.bindProgrammerServices(recorder, recorder.descriptor);
    const auto before = programmer.inspectState();
    std::int32_t result;
    const auto page = signedWord(pageWord), length = signedWord(lengthWord);
    if (kind == 0)
      result = programmer.dumpPage(page);
    else if (kind == 1)
      result = programmer.verifyPage(page, data.data(), length);
    else {
      require(kind == 2);
      result = programmer.writePage(page, data.data(), length);
    }
    const auto after = programmer.inspectState();
    require(before.descriptor == after.descriptor &&
            before.image == after.image && before.length == after.length &&
            before.listener == after.listener);
    require(hex(data.data(), data.size()) == dataHex);
    std::cout << "{\"return_word\":" << static_cast<std::uint32_t>(result)
              << ",\"events\":[";
    for (unsigned i = 0; i < recorder.events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << recorder.events[i];
    }
    std::cout << "]}\n";
  }
  require(std::cin.eof());
}
