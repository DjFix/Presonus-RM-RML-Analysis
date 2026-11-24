#include "presonus/link/Messenger.hpp"
#include <iostream>
int main() {
  Presonus::Link::Messenger first, second;
  second.release();
  for (auto *messenger : {&first, &second, Presonus::Link::getMessenger()}) {
    const bool before = messenger->releaseRequested();
    messenger->start();
    if (messenger->releaseRequested() != before)
      return 1;
    std::cout << "unchanged\n";
  }
}
