#include "presonus/panel/LCDComponent.hpp"

#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>

using Presonus::Panel::Book;
using Presonus::Panel::Control;
using Presonus::Panel::LCDComponent;

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const auto oldIndex = static_cast<std::size_t>(std::atoi(argv[1]));
  const auto newIndex = static_cast<std::size_t>(std::atoi(argv[2]));
  // Incomplete Control is intentional. These aligned pointer identities are
  // compared only. No device Control is created or dereferenced.
  std::max_align_t storage[2]{};
  const std::array<Control *, 3> controls{
      nullptr, reinterpret_cast<Control *>(&storage[0]),
      reinterpret_cast<Control *>(&storage[1])};
  LCDComponent component;
  Book first(12), second(11);
  Book *books[] = {&first, &second};
  component.bindBooks(LCDComponent::Books(books, 2));
  component.bindCurrentBook(&first);
  if (component.editEncoder() != nullptr)
    return 1;
  component.setEditEncoder(controls.at(oldIndex));
  if (component.editEncoder() != controls.at(oldIndex))
    return 1;
  component.setEditEncoder(controls.at(newIndex));
  if (component.editEncoder() != controls.at(newIndex) ||
      component.getBook() != &first || component.getBook(11) != &second ||
      component.getBook(13))
    return 1;
  std::cout << newIndex << '\n';
}
