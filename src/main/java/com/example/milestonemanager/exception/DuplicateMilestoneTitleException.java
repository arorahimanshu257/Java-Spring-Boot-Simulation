package com.example.milestonemanager.exception;

public class DuplicateMilestoneTitleException extends RuntimeException {
    public DuplicateMilestoneTitleException(String message) {
        super(message);
    }
}