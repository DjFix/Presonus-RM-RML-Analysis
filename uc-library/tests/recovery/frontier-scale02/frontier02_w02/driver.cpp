#include "presonus/panel/FXBook.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  int value = static_cast<int>(std::strtoll(argv[1], nullptr, 0));
  auto a = static_cast<std::uintptr_t>(std::strtoull(argv[2], nullptr, 0));
  auto b = static_cast<std::uintptr_t>(std::strtoull(argv[3], nullptr, 0));
  Presonus::Panel::FXBook book(
      value, reinterpret_cast<Presonus::Panel::FxPresetComponent *>(a),
      reinterpret_cast<Core::Portable::Parameter *>(b));
  using presonus::panel::BookInspector;
  using presonus::panel::FXBookInspector;
  std::cout << "[" << BookInspector::initialValue(book) << ","
            << reinterpret_cast<std::uintptr_t>(FXBookInspector::preset(book))
            << ","
            << reinterpret_cast<std::uintptr_t>(
                   FXBookInspector::parameter(book))
            << "," << BookInspector::count(book) << ","
            << BookInspector::zero90(book) << "," << BookInspector::zero94(book)
            << "," << BookInspector::ownsStorage(book) << ","
            << (BookInspector::storage(book) != nullptr) << ","
            << book.isValidPos(0) << "]\n";
}
