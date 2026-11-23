#include "presonus/panel/SceneBook.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>

using Presonus::Panel::Book;
using Presonus::Panel::Page;
using Presonus::Panel::SceneBook;

namespace {
void *scene = nullptr;
std::array<void *, 3> pages{};
std::array<unsigned, 3> deletedPages{};
unsigned pageCount = 0;
bool deletedScene = false;

void release(void *pointer) noexcept {
  if (pointer) {
    if (pointer == scene)
      deletedScene = true;
    for (unsigned i = 0; i < pages.size(); ++i)
      if (pointer == pages[i])
        deletedPages[pageCount++] = i;
  }
  std::free(pointer);
}

[[gnu::noinline]] void deleteScene(SceneBook *pointer) { delete pointer; }
} // namespace

void operator delete(void *pointer) noexcept { release(pointer); }
void operator delete(void *pointer, std::size_t) noexcept { release(pointer); }

int main() {
  unsigned deleting = 0;
  std::string presence;
  while (std::cin >> deleting >> presence) {
    auto *book = new SceneBook(42);
    scene = book;
    pages.fill(nullptr);
    pageCount = 0;
    deletedScene = false;
    if (book->opaqueDispatchIdentity() != 0x32a268 ||
        book->bookState().getTag() != 42)
      return 1;
    // This object is mutable. Populate its actual Book through the existing
    // ownership API for teardown coverage without widening SceneBook's API.
    auto &base = const_cast<Book &>(book->bookState());
    if (presence != "-") {
      for (unsigned i = 0; i < presence.size(); ++i) {
        if (presence[i] == '0')
          base.add(nullptr);
        else {
          if (i >= pages.size() || presence[i] != '1')
            return 1;
          auto owned = std::make_unique<Page>();
          pages[i] = owned.get();
          if (!base.addOwnedPage(owned) || owned)
            return 2;
        }
      }
    }
    if (deleting)
      deleteScene(book);
    else
      book->~SceneBook();

    std::cout << !deletedScene << ' ';
    if (!pageCount)
      std::cout << '-';
    for (unsigned i = 0; i < pageCount; ++i)
      std::cout << deletedPages[i];
    std::cout << '\n';
    scene = nullptr;
    pages.fill(nullptr);
    if (!deleting)
      ::operator delete(book);
  }
  return std::cin.eof() ? 0 : 1;
}
