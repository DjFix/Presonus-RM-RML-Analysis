#include "core/public/corememstream.h"
#include "presonus/application/SimpleReader.hpp"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
std::string hex(const std::string &s) {
  static const char digits[] = "0123456789abcdef";
  std::string result;
  for (unsigned char c : s) {
    result += digits[c >> 4];
    result += digits[c & 15];
  }
  return result;
}
std::string unhex(const std::string &s) {
  std::string result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result += static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16));
  return result;
}
std::vector<std::string> debug;
struct Case {
  std::string op, data, initial, argument, path, expectedOut, expectedSeeks,
      expectedDebug;
  int position, delimiter, fault, faultResult, seekFail, nullWord, exists, open;
  long long seek, expectedResult;
  int expectedPosition, expectedReads, expectedGets;
};
class StreamProbe final : public Core::IO::Stream {
public:
  Core::IO::MemoryStream backing;
  const Case &c;
  int reads = 0, gets = 0;
  std::vector<Core::int64> seeks;
  StreamProbe(std::string &bytes, const Case &c)
      : backing(bytes.data(), static_cast<Core::uint32>(bytes.size())), c(c) {}
  Core::int64 getPosition() override {
    ++gets;
    return backing.getPosition();
  }
  Core::int64 setPosition(Core::int64 p, int mode) override {
    if (mode != Core::IO::kSeekSet)
      std::abort();
    seeks.push_back(p);
    return c.seekFail ? -1 : backing.setPosition(p, mode);
  }
  int readBytes(void *buffer, int size) override {
    if (size != 1)
      std::abort();
    ++reads;
    if (c.fault >= 0 && reads > c.fault)
      return c.faultResult;
    return backing.readBytes(buffer, size);
  }
  int writeBytes(const void *, int) override { std::abort(); }
};
} // namespace

extern "C" void observeDebug(const char *format,
                             ...) asm("__wrap__ZN4Core11DebugPrintfEPKcz");
extern "C" void observeDebug(const char *format, ...) {
  // Test-only application-message observation. Other provider messages are
  // outside the original app-call boundary and are not compared as app logs.
  if (std::string(format).find("getValueForKey:") == std::string::npos)
    return;
  char buffer[8192];
  va_list args;
  va_start(args, format);
  const int size = std::vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);
  if (size < 0 || static_cast<std::size_t>(size) >= sizeof(buffer))
    std::abort();
  debug.push_back(hex(std::string(buffer, size)));
}

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const std::string fileRoot =
      std::filesystem::absolute(argv[3]).lexically_normal().string() + "/";
  std::ifstream input(argv[1]);
  std::string line;
  unsigned count = 0;
  while (std::getline(input, line)) {
    Case c;
    std::istringstream fields(line);
    fields >> c.op >> c.position >> c.delimiter >> c.fault >> c.faultResult >>
        c.seekFail >> c.seek >> c.nullWord >> c.exists >> c.open >>
        std::quoted(c.data) >> std::quoted(c.initial) >>
        std::quoted(c.argument) >> std::quoted(c.path) >> c.expectedResult >>
        std::quoted(c.expectedOut) >> c.expectedPosition >> c.expectedReads >>
        c.expectedGets >> std::quoted(c.expectedSeeks) >>
        std::quoted(c.expectedDebug);
    if (!fields)
      return 3;
    auto bytes = unhex(c.data), argument = unhex(c.argument),
         initial = unhex(c.initial);
    StreamProbe stream(bytes, c);
    stream.backing.setPosition(c.position, Core::IO::kSeekSet);
    Presonus::SimpleReader reader(stream);
    if (c.op != "C1" && c.op != "C2") {
      stream.reads = stream.gets = 0;
      stream.seeks.clear();
      stream.backing.setPosition(c.position, Core::IO::kSeekSet);
    }
    Core::CStringBuffer<64> out(initial.c_str());
    Core::CStringBuffer<256> lineOut(initial.c_str());
    Core::ConstString key(argument.c_str());
    debug.clear();
    long long result = 0;
    if (c.op == "A")
      result = reader.advanceToNextChar(static_cast<char>(c.delimiter));
    else if (c.op == "W")
      result =
          reader.advanceToNextWord(c.nullWord ? nullptr : argument.c_str());
    else if (c.op == "N")
      result = reader.getNextWord(out, static_cast<char>(c.delimiter));
    else if (c.op == "L")
      result = reader.getNextLine(lineOut);
    else if (c.op == "G")
      result = reader.getValueForKey(out, key);
    else if (c.op == "F")
      result = reader.findValueForKey(out, key);
    else if (c.op == "P")
      result = reader.setPosition(c.seek);
    else if (c.op == "S") {
      const auto path = std::filesystem::absolute(c.path).lexically_normal();
      if (path.string().compare(0, fileRoot.size(), fileRoot) != 0)
        return 4;
      std::filesystem::create_directories(path.parent_path());
      if (std::filesystem::exists(path)) {
        std::filesystem::permissions(path, std::filesystem::perms::owner_all);
        std::filesystem::remove(path);
      }
      if (c.exists) {
        std::ofstream file(path, std::ios::binary);
        file.write(bytes.data(), bytes.size());
        file.close();
        std::filesystem::permissions(
            path, c.open ? std::filesystem::perms::owner_read |
                               std::filesystem::perms::owner_write
                         : std::filesystem::perms::owner_read);
      }
      Presonus::SimpleReader::getValueForKey(out, key,
                                             Core::ConstString(path.c_str()));
      if (c.exists) {
        std::ifstream file(path, std::ios::binary);
        std::string retained((std::istreambuf_iterator<char>(file)),
                             std::istreambuf_iterator<char>());
        if (retained != bytes)
          return 5;
      } else if (std::filesystem::exists(path))
        return 6;
    } else if (c.op != "C1" && c.op != "C2")
      return 7;
    std::string actualOut = hex(c.op == "L" ? lineOut.str() : out.str());
    std::string seeks, messages;
    for (auto v : stream.seeks) {
      if (!seeks.empty())
        seeks += ",";
      seeks += std::to_string(v);
    }
    for (const auto &v : debug) {
      if (!messages.empty())
        messages += ",";
      messages += v;
    }
    bool pass = result == c.expectedResult && actualOut == c.expectedOut &&
                messages == c.expectedDebug;
    if (c.op != "S")
      pass = pass && stream.backing.getPosition() == c.expectedPosition &&
             stream.reads == c.expectedReads && stream.gets == c.expectedGets &&
             seeks == c.expectedSeeks;
    if (!pass) {
      std::cerr << "case " << count << " " << c.op << " result=" << result
                << " expected=" << c.expectedResult << " out=" << actualOut
                << " expected=" << c.expectedOut
                << " pos=" << stream.backing.getPosition()
                << " expected=" << c.expectedPosition
                << " reads=" << stream.reads << " expected=" << c.expectedReads
                << " gets=" << stream.gets << " expected=" << c.expectedGets
                << " seeks=" << seeks << " expected=" << c.expectedSeeks
                << " debug=" << messages << " expected=" << c.expectedDebug
                << '\n';
      return 1;
    }
    ++count;
  }
  if (!count)
    return 8;
  std::cout << "passed " << count << " original SimpleReader cases " << argv[2]
            << '\n';
}
