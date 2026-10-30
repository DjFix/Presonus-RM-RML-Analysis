#include "presonus/dice/programmer.hpp"
#include "presonus/dice/programmer_device_services.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include <array>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <linux/spi/spidev.h>
#include <map>
#include <string>
#include <vector>

namespace {
void require(bool value) {
  if (!value)
    std::abort();
}
std::int32_t signedWord(std::uint32_t value) {
  std::int32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
std::string quote(const std::string &text) {
  std::string result = "\"";
  for (const auto c : text) {
    if (c == '\n')
      result += "\\n";
    else if (c == '"' || c == '\\') {
      result += '\\';
      result += c;
    } else
      result += c;
  }
  return result + '"';
}
std::string unhex(const std::string &text) {
  if (text == "-")
    return {};
  std::string result;
  for (std::size_t i = 0; i < text.size(); i += 2)
    result += static_cast<char>(std::stoul(text.substr(i, 2), nullptr, 16));
  return result;
}
std::string hex(const void *input, std::size_t count) {
  static constexpr char digits[] = "0123456789abcdef";
  const auto *data = static_cast<const unsigned char *>(input);
  std::string result;
  for (std::size_t i = 0; i < count; ++i) {
    result += digits[data[i] >> 4];
    result += digits[data[i] & 15];
  }
  return result;
}
struct Case {
  unsigned kind;
  std::uint32_t initial, opened, read, write, mode, jedec, jedecResult,
      manufacturer, closeResult, stdioResult, putError, error;
  std::string path;
};
Case current{};
Presonus::DICE::Dice3Programmer *programmer = nullptr;
std::vector<std::string> events;
std::uint32_t descriptor() {
  require(programmer != nullptr);
  return static_cast<std::uint32_t>(programmer->inspectState().descriptor);
}
class PinIO final : public presonus::surface_panel_port::OutputPinIO {
public:
  unsigned next = 1;
  std::map<std::FILE *, unsigned> files;
  std::map<std::FILE *, bool> live;
  unsigned id(std::FILE *file) {
    require(files.count(file) != 0 && live[file]);
    return files[file];
  }
  std::FILE *open(const char *path, const char *mode) override {
    const auto index = next++;
    auto *file =
        reinterpret_cast<std::FILE *>(std::uintptr_t(0x30000000 + index * 16));
    files[file] = index;
    live[file] = true;
    events.push_back("{\"kind\":\"fopen\",\"path\":" + quote(path) +
                     ",\"mode\":" + quote(mode) +
                     ",\"file\":" + std::to_string(index) + "}");
    return file;
  }
  int printPin(std::FILE *file, const char *format, int pin) override {
    events.push_back("{\"kind\":\"fprintf_pin\",\"file\":" +
                     std::to_string(id(file)) + ",\"format\":" + quote(format) +
                     ",\"pin\":" + std::to_string(pin) + "}");
    return signedWord(current.stdioResult);
  }
  int close(std::FILE *file) override {
    const auto index = id(file);
    live[file] = false;
    events.push_back("{\"kind\":\"fclose\",\"file\":" + std::to_string(index) +
                     "}");
    return signedWord(current.stdioResult);
  }
  void formatPath(char *output, std::size_t capacity, const char *format,
                  int pin) override {
    std::string path = format;
    const auto position = path.find("%d");
    require(position != std::string::npos);
    path.replace(position, 2, std::to_string(pin));
    require(path.size() < capacity);
    std::memcpy(output, path.c_str(), path.size() + 1);
    events.push_back("{\"kind\":\"format_path\",\"format\":" + quote(format) +
                     ",\"pin\":" + std::to_string(pin) +
                     ",\"path\":" + quote(path) + "}");
  }
  std::size_t write(const void *data, std::size_t size, std::size_t count,
                    std::FILE *file) override {
    events.push_back(
        "{\"kind\":\"fwrite\",\"file\":" + std::to_string(id(file)) +
        ",\"size\":" + std::to_string(size) +
        ",\"count\":" + std::to_string(count) +
        ",\"data\":" + quote(hex(data, size * count)) + "}");
    return current.stdioResult;
  }
  int buffering(std::FILE *file, char *, int mode, std::size_t size) override {
    events.push_back(
        "{\"kind\":\"setvbuf\",\"file\":" + std::to_string(id(file)) +
        ",\"mode\":" + std::to_string(mode) +
        ",\"size\":" + std::to_string(size) + "}");
    return signedWord(current.stdioResult);
  }
  int put(int character, std::FILE *file) override {
    events.push_back(
        "{\"kind\":\"fputc\",\"file\":" + std::to_string(id(file)) +
        ",\"character\":" + std::to_string(character) + "}");
    return current.putError ? -1 : character;
  }
  int error() override {
    events.push_back(
        "{\"kind\":\"errno\",\"value\":" + std::to_string(current.error) + "}");
    return signedWord(current.error);
  }
  void log(const char *) override { require(false); }
  void logSet(const char *format, int result, int error) override {
    events.push_back("{\"kind\":\"log_set\",\"format\":" + quote(format) +
                     ",\"result\":" + std::to_string(result) +
                     ",\"error\":" + std::to_string(error) + "}");
  }
  void allClosed() {
    for (const auto &entry : live)
      require(!entry.second);
  }
};
void jedec(std::int32_t fd, unsigned char *receive) {
  events.push_back(
      "{\"kind\":\"jedec\",\"fd\":" +
      std::to_string(static_cast<std::uint32_t>(fd)) +
      ",\"total\":4,\"speed\":1000000,\"bits\":8,\"descriptor_before\":" +
      std::to_string(descriptor()) + "}");
  receive[0] = 0;
  receive[1] = current.manufacturer;
  receive[2] = current.jedec >> 8;
  receive[3] = current.jedec & 255;
}
class Runtime final : public presonus::dice::ProgrammerServices {
public:
  std::int32_t
  transfer(std::int32_t fd,
           const presonus::dice::ProgrammerTransfer &transfer) override {
    require(transfer.transmitLength == 1 && transfer.receiveLength == 3 &&
            transfer.transmit[0] == 0x9f);
    jedec(fd, transfer.receive);
    return signedWord(current.jedecResult);
  }
  std::int64_t clockRawTicks() override { std::abort(); }
  void sleepMilliseconds(std::uint32_t value) override {
    require(value == 1);
    events.push_back("{\"kind\":\"sleep\",\"milliseconds\":1}");
  }
};
} // namespace

extern "C" int __wrap_open(const char *path, int flags, ...) {
  require(flags == 2);
  events.push_back("{\"kind\":\"device_open\",\"path\":" + quote(path) +
                   ",\"flags\":2,\"descriptor_before\":" +
                   std::to_string(descriptor()) + "}");
  return signedWord(current.opened);
}
extern "C" int __wrap_close(int fd) {
  events.push_back("{\"kind\":\"device_close\",\"fd\":" +
                   std::to_string(static_cast<std::uint32_t>(fd)) +
                   ",\"descriptor_before\":" + std::to_string(descriptor()) +
                   "}");
  return signedWord(current.closeResult);
}
extern "C" int __wrap___open_2(const char *path, int flags) {
  return __wrap_open(path, flags);
}
extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  va_list args;
  va_start(args, request);
  void *pointer = va_arg(args, void *);
  va_end(args);
  if (request == SPI_IOC_RD_MODE) {
    auto &mode = *static_cast<std::uint32_t *>(pointer);
    require(mode == 0);
    events.push_back("{\"kind\":\"mode_read\",\"fd\":" +
                     std::to_string(static_cast<std::uint32_t>(fd)) +
                     ",\"before\":0,\"after\":" + std::to_string(current.mode) +
                     ",\"descriptor_before\":" + std::to_string(descriptor()) +
                     "}");
    mode = current.mode;
    return signedWord(current.read);
  }
  if (request == SPI_IOC_WR_MODE) {
    const auto mode = *static_cast<std::uint32_t *>(pointer);
    require(mode == (current.mode & ~std::uint32_t(3)));
    events.push_back("{\"kind\":\"mode_write\",\"fd\":" +
                     std::to_string(static_cast<std::uint32_t>(fd)) +
                     ",\"mode\":" + std::to_string(mode) +
                     ",\"descriptor_before\":" + std::to_string(descriptor()) +
                     "}");
    return signedWord(current.write);
  }
  require(request == SPI_IOC_MESSAGE(1));
  const auto &transfer = *static_cast<spi_ioc_transfer *>(pointer);
  const auto *tx = reinterpret_cast<const unsigned char *>(transfer.tx_buf);
  require(transfer.len == 4 && transfer.speed_hz == 1000000 &&
          transfer.bits_per_word == 8 && tx[0] == 0x9f && tx[1] == 0 &&
          tx[2] == 0 && tx[3] == 0);
  jedec(fd, reinterpret_cast<unsigned char *>(transfer.rx_buf));
  return signedWord(current.jedecResult);
}

int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider-smoke") {
    current = Case{0, 0xffffffff, 7, 0, 0, 0xff, 0x2015,
                   0, 0x20,       0, 0, 0, 0,    "/offline/provider"};
    PinIO io;
    presonus::dice::LinuxProgrammerDeviceServices device(&io);
    presonus::dice::LinuxProgrammerTransport transport;
    presonus::dice::CclProgrammerServices runtime(transport);
    Presonus::DICE::Dice3Programmer instance(nullptr, nullptr, 0);
    programmer = &instance;
    instance.bindProgrammerServices(runtime, -1);
    instance.bindProgrammerDeviceServices(device);
    require(instance.open(current.path.c_str()) == 1 &&
            instance.inspectState().descriptor == 7);
    instance.close();
    require(instance.inspectState().descriptor == 7);
    io.allClosed();
    programmer = nullptr;
    std::cout
        << "PASS real Linux fd/SPI/provider plus actual CCL sleep/buffer and "
           "recovered Panel setup/set; all GPIO/fd/ioctl effects intercepted\n";
    return 0;
  }
  require(argc == 1);
  while (std::cin >> current.kind) {
    std::string pathHex;
    std::cin >> current.initial >> current.opened >> current.read >>
        current.write >> current.mode >> current.jedec >> current.jedecResult >>
        current.manufacturer >> current.closeResult >> current.stdioResult >>
        current.putError >> current.error >> pathHex;
    require(bool(std::cin));
    current.path = unhex(pathHex);
    events.clear();
    PinIO io;
    presonus::dice::LinuxProgrammerDeviceServices device(&io);
    Runtime runtime;
    Presonus::DICE::Dice3Programmer instance(nullptr, nullptr, 0);
    programmer = &instance;
    instance.bindProgrammerServices(runtime, signedWord(current.initial));
    instance.bindProgrammerDeviceServices(device);
    const auto before = instance.inspectState();
    std::int32_t result = 0;
    if (current.kind == 0)
      result = instance.open(current.path.c_str());
    else {
      require(current.kind == 1);
      instance.close();
    }
    const auto after = instance.inspectState();
    require(before.image == after.image && before.length == after.length &&
            before.listener == after.listener);
    io.allClosed();
    std::cout << "{\"events\":[";
    for (unsigned i = 0; i < events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << events[i];
    }
    std::cout << "],\"descriptor_word\":"
              << static_cast<std::uint32_t>(after.descriptor);
    if (current.kind == 0)
      std::cout << ",\"return_word\":" << static_cast<std::uint32_t>(result);
    std::cout << "}\n";
    programmer = nullptr;
  }
  require(std::cin.eof());
}
