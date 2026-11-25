#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/DAWDeviceSlot.hpp"

#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>

using Core::Portable::Component;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::DAWDeviceFolder;
using Presonus::DAWDeviceSlot;

namespace {

struct Cleanup {
  void *receiver = nullptr;
  void *child = nullptr;
  void *parameter = nullptr;
  int receiverDeletes = 0;
  int childDeletes = 0;
  int parameterDeletes = 0;
};

Cleanup cleanup;

template <class Tag, typename Tag::Member member> struct ReadMember {
  friend typename Tag::Member get(Tag) { return member; }
};

struct SlotCache {
  using Member = Parameter *DAWDeviceSlot::*;
  friend Member get(SlotCache);
};

struct FolderCache {
  using Member = Parameter *DAWDeviceFolder::*;
  friend Member get(FolderCache);
};

template struct ReadMember<SlotCache, &DAWDeviceSlot::editParameter>;
template struct ReadMember<FolderCache, &DAWDeviceFolder::countParameter>;

Parameter *cache(const DAWDeviceSlot &slot) { return slot.*get(SlotCache{}); }
Parameter *cache(const DAWDeviceFolder &folder) {
  return folder.*get(FolderCache{});
}

class FeedbackObserver : public Core::Portable::IParamObserver {
public:
  void *castTo(int) override { return nullptr; }
  void paramChanged(Parameter *p, int msg) override {
    if (msg == Parameter::kChanged)
      ++changes;
  }

  int changes = 0;
};

class ForeignChild : public Component {
public:
  void *castTo(int typeId) override {
    if (typeId == DAWDeviceSlot::kTypeID || typeId == DAWDeviceFolder::kTypeID)
      ++visits;
    return Component::castTo(typeId);
  }

  int visits = 0;
};

Parameter *addParameter(Component &component, const char *name, int tag) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = tag;
  std::strcpy(info.name, name);
  info.minValue = -20;
  info.maxValue = 20;
  component.addParameters(&info, 1, true);
  return component.getParameterByTag(tag);
}

int feedback(Parameter *parameter, float value) {
  if (!parameter)
    return 0;
  FeedbackObserver observer;
  auto *previous = parameter->getController();
  parameter->setController(&observer);
  // flushes.
  parameter->setValue(value);
  parameter->setController(previous);
  return observer.changes;
}

void emit(std::initializer_list<int> values) {
  for (int value : values)
    std::cout << value << ' ';
  std::cout << '\n';
}

extern "C" void slotC1(DAWDeviceSlot *) asm("_ZN8Presonus13DAWDeviceSlotC1Ev");
extern "C" void slotC2(DAWDeviceSlot *) asm("_ZN8Presonus13DAWDeviceSlotC2Ev");
extern "C" void slotD0(DAWDeviceSlot *) asm("_ZN8Presonus13DAWDeviceSlotD0Ev");
extern "C" void slotD1(DAWDeviceSlot *) asm("_ZN8Presonus13DAWDeviceSlotD1Ev");
extern "C" void
folderC1(DAWDeviceFolder *) asm("_ZN8Presonus15DAWDeviceFolderC1Ev");
extern "C" void
folderC2(DAWDeviceFolder *) asm("_ZN8Presonus15DAWDeviceFolderC2Ev");
extern "C" void
folderD0(DAWDeviceFolder *) asm("_ZN8Presonus15DAWDeviceFolderD0Ev");
extern "C" void
folderD1(DAWDeviceFolder *) asm("_ZN8Presonus15DAWDeviceFolderD1Ev");

template <class T>
void constructorCase(void (*construct)(T *), unsigned char fill) {
  alignas(T) std::byte storage[sizeof(T)];
  std::memset(storage, fill, sizeof(T));
  auto *object = reinterpret_cast<T *>(storage);
  construct(object);
  object = std::launder(object);
  Component *component = object;
  emit({component->castTo(T::kTypeID) == object,
        static_cast<int>(std::strlen(object->getName())),
        cache(*object) == nullptr, object->getParent() == nullptr,
        object->countChildren(), object->countParameters()});
  object->~T();
}

template <class T> void destructorCase(void (*destroy)(T *), bool populated) {
  auto *object = new T;
  cleanup.receiver = object;
  if (populated) {
    auto *child = new DAWDeviceSlot;
    object->addChild(child);
    cleanup.child = child;
    cleanup.parameter = addParameter(*object, "edit", 2);
  }
  destroy(object);
  emit({cleanup.receiverDeletes != 0, cleanup.receiverDeletes,
        cleanup.childDeletes, cleanup.parameterDeletes});
  if (cleanup.receiverDeletes == 0)
    ::operator delete(object);
}

void getFolderCase(int item) {
  if (item == 0) {
    DAWDeviceSlot slot;
    emit({slot.getFolder() != nullptr, 0});
  } else if (item == 1) {
    ForeignChild parent;
    auto *slot = new DAWDeviceSlot;
    parent.addChild(slot);
    auto *result = slot->getFolder();
    emit({result != nullptr, parent.visits});
  } else {
    class FolderParent : public DAWDeviceFolder {
    public:
      void *castTo(int typeId) override {
        if (typeId == DAWDeviceFolder::kTypeID)
          ++visits;
        return DAWDeviceFolder::castTo(typeId);
      }
      int visits = 0;
    } parent;
    auto *slot = new DAWDeviceSlot;
    parent.addChild(slot);
    auto *result = slot->getFolder();
    emit({result == &parent, parent.visits});
  }
}

void slotInitCase(int item) {
  DAWDeviceSlot slot;
  Parameter *other =
      (item == 1 || item == 2) ? addParameter(slot, "other", 2) : nullptr;
  Parameter *edit = item >= 2 ? addParameter(slot, "edit", 1) : nullptr;
  slot.init();
  if (item == 3)
    slot.init();
  if (cache(slot) != edit)
    std::abort();
  emit({feedback(edit, 1), feedback(other, 1)});
}

void folderInitCase(int item) {
  DAWDeviceFolder folder;
  auto *count = addParameter(folder, "count", 0);
  Parameter *edit = nullptr;
  Parameter *other = nullptr;
  ForeignChild *foreign = nullptr;
  if (item >= 2) {
    foreign = new ForeignChild;
    folder.addChild(foreign);
  }
  if (item >= 1) {
    auto *slot = new DAWDeviceSlot;
    folder.addChild(slot);
    edit = addParameter(*slot, "edit", 1);
  }
  if (item >= 2) {
    auto *slot = new DAWDeviceSlot;
    folder.addChild(slot);
    other = addParameter(*slot, "other", 7);
  }
  folder.init();
  if (cache(folder) != count)
    std::abort();
  emit({feedback(count, 1), feedback(edit, 1), feedback(other, 1),
        foreign ? foreign->visits : 0});
}

void usedCountCase(bool initialize, int children, float value) {
  DAWDeviceFolder folder;
  if (initialize) {
    auto *count = addParameter(folder, "count", 0);
    count->setValue(value);
    folder.init();
  }
  for (int index = 0; index < children; ++index)
    folder.addChild(new Component);
  emit({folder.getUsedCount()});
}

} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *memory) {
  cleanup.receiverDeletes += memory == cleanup.receiver;
  cleanup.childDeletes += memory == cleanup.child;
  cleanup.parameterDeletes += memory == cleanup.parameter;
  __real__ZdlPv(memory);
}

extern "C" void __wrap__ZdlPvm(void *memory, std::size_t size) {
  if (cleanup.receiver && memory == cleanup.receiver)
    std::abort();
  cleanup.childDeletes += memory == cleanup.child;
  cleanup.parameterDeletes += memory == cleanup.parameter;
  __real__ZdlPvm(memory, size);
}

int main(int argc, char **argv) {
  if (argc < 3)
    return 2;
  const std::string_view name = argv[1];
  const int item = std::atoi(argv[2]);
  const bool slot = name.find("DAWDeviceSlot") != std::string_view::npos;
  if (name.ends_with("C1Ev"))
    slot ? constructorCase(slotC1, item) : constructorCase(folderC1, item);
  else if (name.ends_with("C2Ev"))
    slot ? constructorCase(slotC2, item) : constructorCase(folderC2, item);
  else if (name.ends_with("D0Ev"))
    slot ? destructorCase(slotD0, item) : destructorCase(folderD0, item);
  else if (name.ends_with("D1Ev"))
    slot ? destructorCase(slotD1, item) : destructorCase(folderD1, item);
  else if (name.ends_with("6castToEi")) {
    if (slot) {
      DAWDeviceSlot object;
      emit({object.castTo(item) == &object});
    } else {
      DAWDeviceFolder object;
      emit({object.castTo(item) == &object});
    }
  } else if (name.ends_with("9getFolderEv"))
    getFolderCase(item);
  else if (name.ends_with("4initEv"))
    slot ? slotInitCase(item) : folderInitCase(item);
  else if (name.ends_with("12getUsedCountEv") && argc == 5)
    usedCountCase(item, std::atoi(argv[3]), std::strtof(argv[4], nullptr));
  else
    return 2;
}
