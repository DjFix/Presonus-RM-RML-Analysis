#include "presonus/mixer/MixerComponentBaseDelegate.hpp"
#include <iostream>

using Delegate = Presonus::Mixer::MixerComponentBase::Delegate;

struct DefaultObserver : Delegate {
  unsigned marker = 0x12345678;
  void clientsChanged() override {}
};

struct RecordingObserver : DefaultObserver {
  unsigned count = 0;
  bool last = false;
  void notifyStoring(bool storing) override {
    ++count;
    last = storing;
  }
};

void notify(Delegate &observer, bool storing) {
  observer.notifyStoring(storing);
}

int main() {
  bool storing = false;
  while (std::cin >> storing) {
    DefaultObserver fallback;
    RecordingObserver concrete;
    notify(fallback, storing);
    notify(concrete, storing);
    std::cout << fallback.marker << ' ' << concrete.count << ' '
              << concrete.last << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
