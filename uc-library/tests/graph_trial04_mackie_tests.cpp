#include "presonus/MackieControlModel.hpp"
#include <iostream>
int main() {
  int method, tag, state, cached, note, index, count, omit, sink;
  while (std::cin >> method >> tag >> state >> cached >> note >> index >>
         count >> omit >> sink) {
    Presonus::MackieControlModel m;
    for (int i = 0; i < count; ++i)
      m.entries.push_back({100 + i, note, index});
    m.buttonStates.assign(16, static_cast<unsigned char>(cached));
    m.touched.fill(static_cast<unsigned char>(cached));
    m.faderValues.fill(123);
    m.omitMaster = omit;
    if (sink)
      m.midiSink = [](const unsigned char *p, unsigned n, unsigned flags) {
        std::cout << "M" << flags << ":";
        for (unsigned i = 0; i < n; ++i)
          std::cout << unsigned(p[i]) << ",";
        std::cout << ";";
      };
    m.buttonRelease = [](int t, bool b) {
      std::cout << "B" << t << ":" << b << ";";
    };
    m.faderRelease = [](int t, bool b) {
      std::cout << "F" << t << ":" << b << ";";
    };
    m.ledSink = [](int t, bool b) { std::cout << "L" << t << ":" << b << ";"; };
    if (method == 1) {
      const unsigned char bytes[]{0x90, 1, 127};
      m.sendMidiMessage(bytes, 3);
    }
    if (method == 2)
      std::cout << "R" << m.setButtonState(tag, state) << ";";
    if (method == 3)
      m.releaseAllButtons();
    if (method == 4)
      m.resetLeds();
    if (method == 5)
      m.touchFader(tag, state);
    std::cout << " S";
    for (auto x : m.buttonStates)
      std::cout << unsigned(x) << ",";
    std::cout << " T";
    for (auto x : m.touched)
      std::cout << unsigned(x) << ",";
    std::cout << " V";
    for (auto x : m.faderValues)
      std::cout << x << ",";
    std::cout << "\n";
  }
}
