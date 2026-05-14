#!/bin/bash
echo "Restoring payments.py from last committed version..."
git checkout HEAD -- app/payments.py sandbox_app/payments.py
echo "Restored. Current functions:"
grep "^def " app/payments.py
