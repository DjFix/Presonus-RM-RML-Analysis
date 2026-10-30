#include "presonus/avb/streams.hpp"

static_assert(sizeof(unsigned long long) == 8);
static_assert(sizeof(unsigned short) == 2);
static_assert(sizeof(int) == 4);

namespace Presonus::AVB {
AvbListener::AvbListener(unsigned char identifierByte,
                         unsigned long long identifier, unsigned short suffix,
                         int integerWord)
    : state_{identifierByte, identifier, (identifier << 16) | suffix, suffix,
             integerWord} {}

AvbListener::~AvbListener() {}

bool AvbListener::update(unsigned char, unsigned char, unsigned char) {
  return true;
}

AvbTalker::AvbTalker(unsigned char identifierByte, int integerWord)
    : state_{identifierByte, integerWord} {}

AvbTalker::~AvbTalker() {}

bool AvbTalker::update(unsigned char, unsigned char) { return true; }
} // namespace Presonus::AVB
