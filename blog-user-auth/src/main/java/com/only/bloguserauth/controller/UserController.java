package com.only.bloguserauth.controller;


import org.springframework.web.bind.annotation.RestController;

@RestController("/user")
public class UserController {

    public String get(){
        return "hello";
    }
}
