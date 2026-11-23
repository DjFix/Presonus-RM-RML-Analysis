#include "presonus/panel/Book.hpp"

#include <array>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <utility>

using Presonus::Panel::Book;
using presonus::panel::BookInspector;
using presonus::panel::BorrowedBookState;
using Presonus::Panel::Element;
using Presonus::Panel::Page;

namespace {
struct Receiver {
  void *address = nullptr;
  int event = 0;
};

std::array<Receiver, 30> receivers;
std::size_t receiverCount;
std::array<int, 30> events;
std::size_t eventCount;

void watch(void *address, int event) {
  receivers.at(receiverCount++) = {address, event};
}

int takeEvent(void *address, bool sized) {
  for (auto &receiver : receivers) {
    if (receiver.address && address == receiver.address) {
      receiver.address = nullptr;
      return receiver.event + (sized && receiver.event < 200 ? 1000 : 0);
    }
  }
  return 0;
}

void record(int event) {
  if (event)
    events.at(eventCount++) = event;
}

void destroyBook(Book *book) { delete book; }
void (*volatile deleteThroughBook)(Book *) = destroyBook;

struct DerivedBook final : Book {
  using Book::Book;
};

bool registerPages(Book &book, int argc, char **argv) {
  for (int index = 0; index < argc; ++index) {
    const std::string_view layout = argv[index];
    std::unique_ptr<Page> page;
    if (layout != "-") {
      Page::Elements elements;
      for (std::size_t childIndex = 0; childIndex < layout.size();
           ++childIndex) {
        std::unique_ptr<Element> element;
        if (layout[childIndex] == '1') {
          element = std::make_unique<Element>();
          watch(element.get(), 200 + 10 * index + static_cast<int>(childIndex));
        } else if (layout[childIndex] != '0') {
          return false;
        }
        elements.push_back(std::move(element));
      }
      page = std::make_unique<Page>(std::move(elements));
      watch(page.get(), 100 + index);
    }
    if (!book.addOwnedPage(page) || page)
      return false;
  }
  return true;
}

bool borrowedCompatibility() {
  unsigned char first[] = {0, 0, 0, 0, 0, 173};
  const unsigned char *items[] = {first, nullptr};
  BorrowedBookState state(items, 2);
  Book legacy(state);
  if (legacy.isValidPos(0) != 173 || legacy.isValidPos(1) != 0 ||
      legacy.isValidPos(-1) != 0 || legacy.isValidPos(2) != 0 ||
      BookInspector::count(legacy) != 2 || BookInspector::ownsStorage(legacy))
    return false;
  Book legacyCopy(legacy);
  Book assignedLegacy(4);
  assignedLegacy = legacy;
  first[5] = 207;
  if (legacyCopy.isValidPos(0) != 207 || assignedLegacy.isValidPos(0) != 207)
    return false;
  state.slots = Core::ConstVector<const unsigned char *>(items, 0);
  if (BookInspector::count(legacyCopy) != 0 ||
      BookInspector::count(assignedLegacy) != 0 ||
      BookInspector::ownsStorage(assignedLegacy))
    return false;

  auto borrowed = std::make_unique<Page>();
  {
    Book book(13);
    book.add(borrowed.get());
    if (book.isValidPos(0) != 1 || book.getTag() != 13 ||
        BookInspector::count(book) != 1 || !BookInspector::ownsStorage(book))
      return false;
  }
  return borrowed->isEnabled();
}

bool copyCompatibility() {
  Page page;
  Book source(23);
  source.add(&page);
  BookInspector::setActivePosition(source, 1);
  Book copied(source);
  Book assigned(42);
  assigned = source;
  if (BookInspector::storage(copied) == BookInspector::storage(source) ||
      BookInspector::storage(assigned) == BookInspector::storage(source) ||
      BookInspector::storage(assigned) == BookInspector::storage(copied) ||
      copied.getTag() != 23 || assigned.getTag() != 23 ||
      BookInspector::pageAt(copied, 0) != &page ||
      BookInspector::pageAt(assigned, 0) != &page ||
      BookInspector::zero90(assigned) != 1)
    return false;
  source.add(nullptr);
  if (BookInspector::count(copied) != 1 || BookInspector::count(assigned) != 1)
    return false;

  Book owned(17);
  auto holder = std::make_unique<Page>();
  Page *const identity = holder.get();
  if (!owned.addOwnedPage(holder) || holder)
    return false;
  try {
    Book disallowed(owned);
    return false;
  } catch (const std::logic_error &) {
  }
  try {
    copied = owned;
    return false;
  } catch (const std::logic_error &) {
  }
  try {
    owned = assigned;
    return false;
  } catch (const std::logic_error &) {
  }
  Book &sameOwned = owned;
  owned = sameOwned;
  return owned.getActivePage() == identity && owned.getTag() == 17 &&
         BookInspector::count(owned) == 1 && copied.getTag() == 23 &&
         BookInspector::count(copied) == 1 &&
         BookInspector::pageAt(copied, 0) == &page;
}
} // namespace

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;

extern "C" void __wrap__ZdlPv(void *address) noexcept {
  const int event = takeEvent(address, false);
  __real__ZdlPv(address);
  record(event);
}

extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) noexcept {
  const int event = takeEvent(address, true);
  __real__ZdlPvm(address, size);
  record(event);
}

int main(int argc, char **argv) {
  if (argc < 2 || !borrowedCompatibility() || !copyCompatibility())
    return 2;
  const int variant = argv[1][0] - '0';
  if (variant == 0) {
    auto *book = new Book(0);
    watch(book, 90);
    if (!registerPages(*book, argc - 2, argv + 2)) {
      deleteThroughBook(book);
      return 2;
    }
    deleteThroughBook(book);
  } else if (variant == 1) {
    Book book(0);
    watch(&book, 90);
    if (!registerPages(book, argc - 2, argv + 2))
      return 2;
  } else if (variant == 2) {
    DerivedBook book(0);
    watch(static_cast<Book *>(&book), 90);
    if (!registerPages(book, argc - 2, argv + 2))
      return 2;
  } else {
    return 2;
  }
  for (std::size_t index = 0; index < eventCount; ++index)
    std::cout << events[index] << ' ';
  std::cout << '\n';
}
