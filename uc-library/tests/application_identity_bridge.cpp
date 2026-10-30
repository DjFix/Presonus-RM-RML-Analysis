#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "presonus/application/SurfaceApplication.hpp"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace {
void require(bool value) {
  if (!value)
    std::abort();
}
using Buffer = Core::CStringBuffer<32>;
std::unordered_map<unsigned, std::unique_ptr<Buffer>> buffers;
std::vector<std::string> trace;
unsigned nextId = 1;
std::string hex(const std::string &s) {
  constexpr char digits[] = "0123456789abcdef";
  std::string out;
  for (unsigned char byte : s) {
    out += digits[byte >> 4];
    out += digits[byte & 15];
  }
  return out.empty() ? "-" : out;
}
std::string unhex(const std::string &s) {
  if (s == "-")
    return {};
  require(s.size() % 2 == 0);
  std::string out;
  for (std::size_t i = 0; i < s.size(); i += 2)
    out += static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16));
  return out;
}
} // namespace
int scan(const char *text, const char *format, va_list args) {
  require(std::string(format) == "%u" || std::string(format) == "%08u");
  va_list observed;
  va_copy(observed, args);
  auto *out = va_arg(observed, unsigned *);
  va_end(observed);
  const int result = std::vsscanf(text, format, args);
  trace.push_back("scan " + hex(text) + " " + hex(format) + " " +
                  std::to_string(result) + " " + std::to_string(*out));
  return result;
}
extern "C" int __wrap___isoc99_sscanf(const char *text, const char *format,
                                      ...) {
  va_list args;
  va_start(args, format);
  const int result = scan(text, format, args);
  va_end(args);
  return result;
}
extern "C" int __wrap___isoc23_sscanf(const char *text, const char *format,
                                      ...) {
  va_list args;
  va_start(args, format);
  const int result = scan(text, format, args);
  va_end(args);
  return result;
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  require(std::string(format) ==
          "Generated alternate AVB MAC 0x%x from 0x%x\n");
  va_list args;
  va_start(args, format);
  const unsigned value = va_arg(args, unsigned),
                 serial = va_arg(args, unsigned);
  va_end(args);
  trace.push_back("debug " + hex(format) + " " + std::to_string(value) + " " +
                  std::to_string(serial));
}
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op, arg;
    in >> op;
    if (op == "reset") {
      buffers.clear();
      trace.clear();
      nextId = 1;
      std::cout << "OK\n";
    } else if (op == "new") {
      const unsigned id = nextId++;
      buffers[id] = std::make_unique<Buffer>();
      std::cout << id << '\n';
    } else if (op == "format") {
      unsigned id;
      in >> id >> arg;
      const auto format = unhex(arg);
      if (format == "%08u") {
        unsigned value;
        in >> value;
        buffers.at(id)->appendFormat("%08u", value);
      } else {
        require(format == "%02d%02d%04d");
        int a, b, c;
        in >> a >> b >> c;
        buffers.at(id)->appendFormat("%02d%02d%04d", a, b, c);
      }
      std::cout << hex(buffers.at(id)->str()) << '\n';
    } else if (op == "substring") {
      unsigned source, target;
      int start, count;
      in >> source >> target >> start >> count;
      buffers.at(source)->subString(*buffers.at(target), start, count);
      std::cout << hex(buffers.at(target)->str()) << '\n';
    } else if (op == "scan") {
      std::string fmt;
      in >> arg >> fmt;
      const auto text = unhex(arg), format = unhex(fmt);
      unsigned value = 0;
      const int result =
          __wrap___isoc99_sscanf(text.c_str(), format.c_str(), &value);
      std::cout << result << ' ' << value << '\n';
    } else if (op == "debug") {
      unsigned value, serial;
      in >> value >> serial;
      __wrap__ZN4Core11DebugPrintfEPKcz(
          "Generated alternate AVB MAC 0x%x from 0x%x\n", value, serial);
      std::cout << "OK\n";
    } else if (op == "native") {
      unsigned serial;
      in >> arg >> serial;
      require(arg == "alternate" || arg == "network");
      Presonus::Surface::SurfaceApplication app;
      presonus::application::SurfaceSerialStateAccess::seed(app, serial);
      const auto result =
          arg == "alternate" ? app.getAlternateMac() : app.getNetworkSerial();
      require(presonus::application::SurfaceSerialStateAccess::value(app) ==
              serial);
      std::cout << result << '\n';
    } else if (op == "trace") {
      std::cout << trace.size();
      for (const auto &entry : trace)
        std::cout << ' ' << hex(entry);
      std::cout << '\n';
    } else if (op == "quit") {
      std::cout << "OK\n" << std::flush;
      return 0;
    } else
      return 2;
    std::cout << std::flush;
  }
  return 3;
}
