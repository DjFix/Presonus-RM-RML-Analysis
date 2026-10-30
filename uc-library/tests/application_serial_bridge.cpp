#include "core/portable/corefile.h"
#include "presonus/application/SimpleReader.hpp"
#include "presonus/application/SurfaceApplication.hpp"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace {
void require(bool condition) {
  if (!condition)
    std::abort();
}
std::filesystem::path root, fixture;
std::vector<std::string> trace;
FILE *tracked = nullptr;
std::string hex(const std::string &s) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string out;
  for (unsigned char c : s) {
    out += digits[c >> 4];
    out += digits[c & 15];
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
extern "C" FILE *__real_fopen(const char *, const char *);
extern "C" int __real_fclose(FILE *);
extern "C" FILE *__wrap_fopen(const char *name, const char *mode) {
  require(std::string(name) == "/sfs/hwaddr.txt");
  require(!fixture.empty() && fixture.parent_path() == root);
  require(!std::filesystem::is_symlink(fixture));
  FILE *file = __real_fopen(fixture.c_str(), mode);
  tracked = file;
  trace.push_back(std::string("open ") + mode + " " + (file ? "1" : "0"));
  return file;
}
extern "C" int __wrap_fclose(FILE *file) {
  require(file == tracked);
  const int result = __real_fclose(file);
  tracked = nullptr;
  trace.push_back("close " + std::to_string(result));
  return result;
}
extern "C" int __wrap___isoc99_sscanf(const char *text, const char *format,
                                      ...) {
  require(std::string(format) == "%llx");
  va_list args;
  va_start(args, format);
  const int result = std::vsscanf(text, format, args);
  va_end(args);
  trace.push_back("scan " + hex(text) + " " + std::to_string(result));
  return result;
}

int main(int argc, char **argv) {
  require(argc == 2);
  root = std::filesystem::canonical(argv[1]);
  require(root.is_absolute());
  std::unique_ptr<Core::Portable::FileStream> stream;
  std::unique_ptr<Presonus::SimpleReader> reader;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    std::string command, arg;
    input >> command;
    if (command == "use") {
      require(!stream && !tracked);
      input >> arg;
      require(!arg.empty() && arg.find('/') == std::string::npos &&
              arg != "." && arg != "..");
      fixture = root / arg;
      trace.clear();
      std::cout << "OK\n";
    } else if (command == "arm_open") {
      require(!stream);
      stream = std::make_unique<Core::Portable::FileStream>();
      std::cout << stream->open("/sfs/hwaddr.txt", 3) << '\n';
    } else if (command == "arm_reader") {
      require(stream && !reader);
      reader = std::make_unique<Presonus::SimpleReader>(*stream);
      std::cout << "OK\n";
    } else if (command == "arm_word") {
      require(static_cast<bool>(reader));
      Core::CStringBuffer<64> word;
      const bool result = reader->getNextWord(word, ':');
      std::cout << result << ' ' << hex(word.str()) << '\n';
    } else if (command == "cstring") {
      unsigned size;
      input >> size;
      require(size == 64 || size == 128);
      Core::CStringBuffer<64> small;
      Core::CStringBuffer<128> large;
      std::cout << hex(size == 64 ? small.str() : large.str()) << '\n';
    } else if (command == "scan") {
      input >> arg;
      const std::string text = unhex(arg);
      unsigned long long value = 0;
      const int result = std::sscanf(text.c_str(), "%llx", &value);
      std::cout << result << ' ' << value << '\n';
    } else if (command == "arm_close") {
      reader.reset();
      stream.reset();
      std::cout << "OK\n";
    } else if (command == "native") {
      unsigned long long seed;
      input >> seed;
      Presonus::Surface::SurfaceApplication app;
      presonus::application::SurfaceSerialStateAccess::seed(app, seed);
      app.readSerialFromDisk();
      std::cout << presonus::application::SurfaceSerialStateAccess::value(app)
                << '\n';
    } else if (command == "trace") {
      std::cout << trace.size();
      for (const auto &entry : trace)
        std::cout << ' ' << hex(entry);
      std::cout << '\n';
    } else if (command == "quit") {
      require(!stream && !tracked);
      std::cout << "OK\n" << std::flush;
      return 0;
    } else {
      std::cerr << "unknown command\n";
      return 2;
    }
    std::cout << std::flush;
  }
  return 3;
}
