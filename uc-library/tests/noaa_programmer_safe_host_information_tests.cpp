#include "presonus/noaa/programmer.hpp"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
using namespace presonus::noaa;
std::string hex(const char *value) {
  static const char digits[] = "0123456789abcdef";
  std::string out;
  for (; *value; ++value) {
    const auto c = static_cast<unsigned char>(*value);
    out += digits[c >> 4];
    out += digits[c & 15];
  }
  return out.empty() ? "-" : out;
}
struct Script : ProgrammerReceiveServices,
                ProgrammerTransport,
                ProgrammerInformationServices {
  std::int64_t start, step;
  unsigned clocks = 0, reads = 0;
  int writeReturn;
  std::vector<std::pair<int, unsigned>> input;
  std::vector<std::string> events;
  std::int64_t clockRawTicks() override {
    auto t = start + step * clocks++;
    events.push_back("C:" + std::to_string(t));
    return t;
  }
  std::int32_t readByte(std::int32_t fd, unsigned char *byte) override {
    auto r = input[std::min<std::size_t>(reads++, input.size() - 1)];
    if (r.first > 0)
      *byte = static_cast<unsigned char>(r.second);
    events.push_back("R:" + std::to_string(fd) + ":" + std::to_string(r.first) +
                     ":" + (r.first > 0 ? std::to_string(r.second) : "-"));
    return r.first;
  }
  void debugMessage(const char *message) override {
    events.push_back("D:" + hex(message));
  }
  void responseTimeout() override { debugMessage("waitResponse timeout. \n"); }
  void responseReadError(std::int32_t value) override {
    events.push_back("E:" + std::to_string(value));
  }
  std::int32_t write(std::int32_t fd, const unsigned char *bytes,
                     std::uint32_t count) override {
    assert(count == 1);
    events.push_back("W:" + std::to_string(fd) + ":" + std::to_string(*bytes));
    return writeReturn;
  }
  void partID(std::uint32_t value) override {
    events.push_back("I:" + std::to_string(value));
  }
  void bootloaderVersion(std::uint32_t a, std::uint32_t b) override {
    events.push_back("V:" + std::to_string(a) + ":" + std::to_string(b));
  }
  void eraseCommand(unsigned char value) override {
    events.push_back("X:" + std::to_string(value));
  }
  std::int32_t close(std::int32_t) override { return -1; }
};
struct Listener : Presonus::UC::IFirmwareUpdateListener {
  Script &script;
  explicit Listener(Script &s) : script(s) {};
  void onProgress(const char *text, float value) override {
    std::uint32_t bits;
    std::memcpy(&bits, &value, 4);
    script.events.push_back("L:" + hex(text) + ":" + std::to_string(bits));
  }
};
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream file(argv[1]);
  assert(file);
  std::string line;
  unsigned cases = 0;
  while (std::getline(file, line)) {
    std::istringstream in(line);
    std::string method;
    int arg, fd, emit;
    bool hasListener;
    std::int64_t epoch;
    unsigned n;
    Script script;
    in >> method >> arg >> fd >> script.start >> script.step >>
        script.writeReturn >> hasListener >> emit >> epoch >> n;
    for (unsigned i = 0; i < n; ++i) {
      int ret;
      unsigned byte;
      in >> ret >> byte;
      script.input.emplace_back(ret, byte);
    }
    std::array<std::uint32_t, 4> initialInfo, expectedInfo;
    for (auto &v : initialInfo)
      in >> v;
    std::uint32_t expected;
    std::string response;
    unsigned en;
    in >> expected >> response;
    for (auto &v : expectedInfo)
      in >> v;
    in >> en;
    std::vector<std::string> events;
    for (unsigned i = 0; i < en; ++i) {
      std::string e;
      in >> e;
      events.push_back(e);
    }
    assert(in);
    Listener listener(script);
    Presonus::NOAA::TCardProgrammer object(hasListener ? &listener : nullptr,
                                           nullptr, 0);
    ProgrammerAccess::bind(object, script, fd);
    ProgrammerAccess::bindReceive(object, script);
    ProgrammerAccess::bindInformation(object, script);
    ProgrammerAccess::mutableState(object).words28to40 = initialInfo;
    ProgrammerAccess::mutableState(object).response.fill(0xa5);
    setProgrammerProgressEpochMilliseconds(epoch);
    std::int32_t result = 0;
    if (method == "printInfo")
      object.printInfo();
    else if (method == "getChipID")
      result = object.getChipID();
    else if (method == "readInfo")
      result = object.readInfo();
    else if (method == "waitResponse")
      result = object.waitResponse(arg);
    else if (method == "getNextChar")
      result = object.getNextChar(arg);
    else if (method == "waitAck")
      result = object.waitAck(arg);
    else if (method == "sync")
      result = object.sync();
    else if (method == "doCommand")
      result = object.doCommand(static_cast<unsigned char>(arg));
    else if (method == "printProgress")
      object.printProgress("safe info", emit != 0);
    else
      std::abort();
    if (method != "printProgress" && method != "printInfo" &&
        static_cast<std::uint32_t>(result) != expected) {
      std::fprintf(stderr, "result case%u\n", cases);
      std::abort();
    }
    if (script.events != events) {
      std::fprintf(stderr, "events case%u method%s\n", cases, method.c_str());
      for (auto &e : script.events)
        std::fprintf(stderr, "actual %s\n", e.c_str());
      for (auto &e : events)
        std::fprintf(stderr, "expect %s\n", e.c_str());
      std::abort();
    }
    std::string actual;
    static const char digits[] = "0123456789abcdef";
    for (auto byte : ProgrammerAccess::state(object).response) {
      actual += digits[byte >> 4];
      actual += digits[byte & 15];
    }
    assert(actual == response);
    assert(ProgrammerAccess::state(object).words28to40 == expectedInfo);
    ++cases;
  }
  assert(cases == 8878);
  std::printf("{\"passed\":true,\"cases\":%u,\"hardware_operations\":0}\n",
              cases);
}
