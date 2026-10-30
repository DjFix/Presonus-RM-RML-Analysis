#pragma once
#include "core/public/coreintrusivelist.h"
#include "presonus/uc/events.hpp"
#include <map>
#include <memory>
#include <vector>

namespace Presonus::UC {
// Original RTTI proves the public Core::IntrusiveLink<EventItem> base. The
// pinned upstream implementation supplies actual link storage/operations; its
// native offset/layout differs from original ARM+4. No binary ABI claim.
// getData reference return remains a portable declaration choice.
class EventItem : public Core::IntrusiveLink<EventItem> {
public:
  virtual ~EventItem();
  virtual Event &getData() = 0;
};
class EventFactory;
} // namespace Presonus::UC

namespace presonus::uc {
struct DefaultFactorySourceAccess;
// Independent integration contracts replacing original class-vtable and Core
// container storage, not recovered original methods. All callbacks must exist.
// read may receive null only if that callback explicitly supports null items.
struct FactoryCodec {
  void *context = nullptr;
  Presonus::UC::EventItem *(*create)(void *) = nullptr;
  Presonus::UC::EventItem *(*clone)(void *,
                                    const Presonus::UC::Event &) = nullptr;
  bool (*write)(void *, Presonus::UC::BufferWriter &,
                const Presonus::UC::Event &) = nullptr;
  bool (*read)(void *, Presonus::UC::EventItem *,
               Presonus::UC::BufferReader &) = nullptr;
  void (*destroy)(void *, Presonus::UC::EventItem *) = nullptr;
};
struct FactoryRegistration {
  int type;
  const FactoryCodec *codec;
};
struct FactoryRegistry {
  // A positive modulus and correctly bucketed entries are required. Signed
  // remainder buckets preserve the observed hash even for negative type bits.
  int modulus = 8;
  std::map<int, std::vector<FactoryRegistration>> buckets;
  const FactoryCodec *fallback = nullptr;
  // Optional actual-source backend. get must distinguish found-null from miss.
  void *sourceBackendContext = nullptr;
  bool (*sourceBackendGet)(void *, const FactoryCodec *&, int) = nullptr;
  void (*sourceBackendAppend)(void *, int, const FactoryCodec *) = nullptr;
  void append(int type, const FactoryCodec *codec);
};
} // namespace presonus::uc

namespace Presonus::UC {
class EventFactory {
public:
  EventFactory();
  explicit EventFactory(presonus::uc::FactoryRegistry &registry);
  ~EventFactory();
  template <class T> void addClass();
  EventFactory(const EventFactory &) = delete;
  EventFactory &operator=(const EventFactory &) = delete;
  static int hashEventType(const int &type, int modulus);
  EventItem *create(const Event &event);
  EventItem *createType(int type);
  bool write(BufferWriter &writer, const Event &event);
  int write(char *data, int capacity, const Event &event);
  EventItem *read(BufferReader &reader);
  EventItem *read(const char *data, int capacity);

private:
  const presonus::uc::FactoryCodec *find(int type) const;
  friend struct presonus::uc::DefaultFactorySourceAccess;
  struct SourceOwned;
  std::unique_ptr<SourceOwned> owned_;
  presonus::uc::FactoryRegistry &registry_;
};
// Return spellings of these non-template original methods are unencoded.
// Portable declarations express the observed integer, bool and item-address
// contracts; matching mangles do not establish original headers or ARM ABI.
} // namespace Presonus::UC
