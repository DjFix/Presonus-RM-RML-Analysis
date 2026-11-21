#pragma once

// Portable return type. The original declaration's return type is unresolved.
// The input is a readable table terminated by -1. The count must fit int.
int countTableElements(const int *table);
