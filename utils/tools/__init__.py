# coding=utf-8
from . import control_tools, datetime_tools, numeric_tools, process_tools, screen_tools, string_tools
from .control_tools import *
from .datetime_tools import *
from .numeric_tools import *
from .process_tools import *
from .screen_tools import *
from .string_tools import *

# TODO: TA Login
# https://ta.bi.com/
"""
<body>
	<form name="loginForm" class="loginForm" id="loginForm" onsubmit="javascript:return WebForm_OnSubmit();" action="./login.aspx" method="post">
        <div id="centeredDiv">
            <div id="body">
                <div id="loginbox">
                    <div class="loginRow" id="loginUsername">
                        <label>User Name:</label>
                        <input name="logAppLogin$UserName" tabindex="1" class="inputF" id="logAppLogin_UserName" type="text">
                        <span class="val" id="logAppLogin_UserNameRequired" style="color: red; visibility: hidden;">*</span>
                    </div>
                    <div class="loginRow" id="loginPassword">
                        <label>Password:</label>
                        <input name="logAppLogin$Password" tabindex="2" class="inputF" id="logAppLogin_Password" type="password">
                        <span class="val" id="logAppLogin_PasswordRequired" style="color: red; visibility: hidden;">*</span>
                    </div>
                    <div class="loginRow">
                        <input name="logAppLogin$Login" tabindex="4" class="loginBtn" id="logAppLogin_Login" style="border-width: 0px;" onmousedown="src='Image/Login-button-p.png'" onmouseup="src='Image/Login-button.png'" onclick='javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions("logAppLogin$Login", "", true, "", "", false, false))' type="image" src="Image/Login-button.png" text="Login">
                    </div>
                </div>
            </div>
        </div>
	</form>
</body>
"""
