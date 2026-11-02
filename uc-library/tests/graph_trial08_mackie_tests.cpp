#include "presonus/MackieControlModel.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
using Model = Presonus::MackieControlModel;
static int number(const char *s) {
  return static_cast<int>(std::strtol(s, nullptr, 10));
}
static void rows(const std::vector<Model::Entry> &v) {
  std::cout << '[';
  bool first = true;
  for (const auto &e : v) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << '[' << e.tag << ',' << e.note << ',' << e.stateIndex << ']';
  }
  std::cout << ']';
}
int main(int argc, char **argv) {
  if (argc < 3)
    return 2;
  Model m;
  int method = number(argv[1]), a = number(argv[2]);
  if (method == 1 || method == 2) {
    if (argc != 4)
      return 2;
    int b = number(argv[3]);
    Model::Entry x{a, a, 0}, y{b, b, 0};
    std::cout << (method == 1 ? m.compareEntryMidiNotes(&x, &y)
                              : m.compareEntryTags(&x, &y));
  } else if (method == 10) {
    m.midiSink = [](const unsigned char *p, unsigned n, unsigned) {
      for (unsigned i = 0; i < n; ++i)
        std::cout << unsigned(p[i]) << ' ';
      std::cout << '\n';
    };
    m.turnScrubwheel(a);
  } else if (method == 8 || method == 9) {
    if ((argc - 3) % 3)
      return 2;
    auto &v = method == 8 ? m.midiEntries : m.entries;
    for (int i = 3; i < argc; i += 3)
      v.push_back({number(argv[i]), number(argv[i + 1]), number(argv[i + 2])});
    auto *r = method == 8 ? m.getEntryByMidiNote(a) : m.getEntryByTag(a);
    std::cout << (r ? r - v.data() : -1);
  } else if (method == 3) {
    if (argc != 5)
      return 2;
    for (int i = 0; i < a; ++i) {
      m.entries.push_back({i * 2, i * 2, i});
      m.midiEntries.push_back({i * 2, i * 2, i});
      m.buttonStates.push_back(1);
    }
    m.addMapping(number(argv[3]), number(argv[4]));
    std::cout << "{\"tags\":";
    rows(m.entries);
    std::cout << ",\"midi\":";
    rows(m.midiEntries);
    std::cout << ",\"buttons\":[";
    for (unsigned i = 0; i < m.buttonStates.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << unsigned(m.buttonStates[i]);
    }
    std::cout << "]}";
  } else if (method >= 4 && method <= 7) {
    if (argc != 5)
      return 2;
    unsigned state = static_cast<unsigned>(std::strtoul(argv[3], nullptr, 10)),
             bits = static_cast<unsigned>(std::strtoul(argv[4], nullptr, 10));
    m.connectionState = state;
    m.touched.fill(static_cast<unsigned char>(state));
    std::memcpy(m.assignmentData.data(), "ABX", 3);
    std::memcpy(m.timecodeData.data(), "0123456789X", 11);
    bool first = true;
    std::cout << "{\"trace\":[";
    auto sep = [&]() {
      if (!first)
        std::cout << ',';
      first = false;
    };
    m.connectionInitializer = [&]() {
      sep();
      std::cout << "{\"slot\":52,\"state\":" << m.connectionState << '}';
    };
    m.textSink = [&](int tag, const char *s) {
      sep();
      std::cout << "{\"slot\":28,\"tag\":" << tag << ",\"text\":\"" << s
                << "\"}";
    };
    m.faderValueSink = [&](int tag, float value) {
      unsigned v;
      std::memcpy(&v, &value, 4);
      sep();
      std::cout << "{\"slot\":16,\"tag\":" << tag << ",\"float_bits\":" << v
                << '}';
    };
    if (method == 4)
      m.initConnection();
    if (method == 5)
      m.updateAssignmentData();
    if (method == 6)
      m.updateTimecodeData();
    if (method == 7) {
      float value;
      std::memcpy(&value, &bits, 4);
      m.onMessageFaderValue(a, value);
    }
    std::cout << "],\"connection\":" << m.connectionState
              << ",\"assignment\":\"";
    auto hex = [](const auto &v) {
      const char *digits = "0123456789abcdef";
      for (unsigned char c : v)
        std::cout << digits[c >> 4] << digits[c & 15];
    };
    hex(m.assignmentData);
    std::cout << "\",\"timecode\":\"";
    hex(m.timecodeData);
    std::cout << "\"}";
  } else
    return 2;
}
