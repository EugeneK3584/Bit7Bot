##########################################################################################################
import pytest
import time
import json
import re
import sys
import os
import shelve
import urllib.request

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementClickInterceptedException
from collections import namedtuple
from inputimeout import inputimeout, TimeoutOccurred
from time import sleep

##########################################################################################################
DefaultExternalIP = '96.47.229.171'

TIME_TIMEOUT = 10 # 10 seconds global timeout default
choice = 1 # default option

isLongPosition = False
LongPositionAmount = 0.0
LongPositionCutLoss = 0.0
LongPositionPNLPrev = 0.0
LongPositionPNLCur = 0.0
LongPositionPNL = 0.0
LongPositionLev = 0.0
isShortPosition = False
ShortPositionAmount = 0.0
ShortPositionCutLoss = 0.0
ShortPositionPNLPrev = 0.0
ShortPositionPNLCur = 0.0
ShortPositionPNL = 0.0
ShortPositionLev = 0.0
isLongALCM = False
OrderLongAmount = 0.0
OrderLongPrice = 0.0
OrderLongLev = 0.0
isShortALCM = False
OrderShortAmount = 0.0
OrderShortPrice = 0.0
OrderShortLev = 0.0
diff = 0.0

firstrunFlag = True
cancelFlag = False

isShortTrailingActive = False
isLongTrailingActive = False

##########################################################################################################
def IsSellLong():
# This function returns true/false for sell signal based on PNL for Long position
 
 PNLScalingFactor = 5 # trailing stop trigger exit signal if PNL goes down <10%-10%/5, 50%-50%/5, 100%-100%/5
 TrailingPNL = 10 # trailing stop activated

 global LongPositionPNLPrev
 global LongPositionPNL
 global isLongTrailingActive

 if ( LongPositionPNL > 0.0 ) and ( LongPositionPNLPrev > 0.0 ):
    print ('PNL check cycle for position LONG')
    
    if (LongPositionPNL > (TrailingPNL + TrailingPNL/PNLScalingFactor + 1)):
    #
       if ( isLongTrailingActive is False):
          print ('Position LONG trailing stop is actived ! ', LongPositionPNL)      
          isLongTrailingActive = True
       else:
          print ('Position LONG trailing stop is already active ', LongPositionPNL)      

       if ((LongPositionPNL - LongPositionPNL/PNLScalingFactor) >= LongPositionPNLPrev): 
          print ('PNL Position LONG in uptrend, stay ', LongPositionPNL)
          LongPositionPNLPrev = LongPositionPNL
          return False

       elif ((LongPositionPNL - LongPositionPNL/PNLScalingFactor) < LongPositionPNLPrev): 
            print ('PNL Position LONG in downtrend, sell ! ', LongPositionPNL)
            LongPositionPNLPrev = LongPositionPNL
            return True

    # locking trailing stop
    else:
         print ('Waiting to lock trailing stop for position LONG ', LongPositionPNL)         
         LongPositionPNLPrev = LongPositionPNL         
         return False

 elif ( LongPositionPNL < 0.0 ) and ( LongPositionPNL < 0.0 ):
      print ('Negative PNL for position LONG !, staying ', LongPositionPNL) 
      LongPositionPNLPrev = LongPositionPNL      
      return False

 elif ( LongPositionPNLPrev == 0.0 ):
      print ('PNL check for position LONG cant run on first start ', LongPositionPNL)
      LongPositionPNLPrev = LongPositionPNL
      return False

##########################################################################################################
def IsSellShort():
# This function returns true/false for sell signal based on PNL for Short position
 
 PNLScalingFactor = 5 # trailing stop trigger exit signal if PNL goes down <10%-10%/5, 50%-50%/5, 100%-100%/5
 TrailingPNL = 10 # trailing stop activated

 global ShortPositionPNLPrev
 global ShortPositionPNL
 global isShortTrailingActive

 if ( ShortPositionPNL > 0.0 ) and ( ShortPositionPNLPrev > 0.0 ):
    print ('PNL check cycle for position SHORT')
    
    if (ShortPositionPNL > (TrailingPNL + TrailingPNL/PNLScalingFactor + 1)):
    #
       if ( isShortTrailingActive is False):
          print ('Trailing stop for position SHORT is actived ! ', ShortPositionPNL) 
          isShortTrailingActive = True
       else:
          print ('Trailing stop for position SHORT is already active ', ShortPositionPNL)


       if ((ShortPositionPNL - ShortPositionPNL/PNLScalingFactor) >= ShortPositionPNLPrev): 
          print ('PNL Position SHORT in uptrend, stay ', ShortPositionPNL)
          ShortPositionPNLPrev = ShortPositionPNL
          return False

       elif ((ShortPositionPNL - ShortPositionPNL/PNLScalingFactor) < ShortPositionPNLPrev): 
            print ('PNL Position SHORT in downtrend, sell ! ', ShortPositionPNL )
            ShortPositionPNLPrev = ShortPositionPNL
            return True

    # locking trailing stop
    else:
         print ('Waiting to lock trailing stop for order SHORT ', ShortPositionPNL)
         ShortPositionPNLPrev = ShortPositionPNL         
         return False

 elif ( ShortPositionPNL < 0.0 ):
      print ('Negative PNL for position SHORT !, staying ', ShortPositionPNL) 
      ShortPositionPNLPrev = ShortPositionPNL      
      return False

 elif ( ShortPositionPNLPrev == 0.0 ):
      print ('PNL check for position SHORT cant run on first start')
      ShortPositionPNLPrev = ShortPositionPNL
      return False

##########################################################################################################

def OpenedPositionsLong(driver):

   LongPosition = namedtuple ("LongPosition", ["Amount", "CutLoss", "PNL", "Lev"])  

   Amount = 0.0
   CutLoss = 0.00
   PNL = 0.00
   PNL_t = ''   
   Lev = 0.0

   try:
        print ('Opened LONG Positions test is running')
        sleep(1)        
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"#tpositions")]'))   
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()
        sleep(1)

        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tbPositionList"]/tr'))   
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        sleep(1)

        row_count = len(driver.find_elements(By.XPATH, '//*[@id="tbPositionList"]/tr'))
        #column_count = len(driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr/td"))
        if row_count > 0 :

           for row in driver.find_elements(By.XPATH, '//*[@id="tbPositionList"]/tr'): 
               positionDirection = row.find_elements(By.TAG_NAME, "td")[1]

               if positionDirection.text == "UP" :
                  cell = row.find_elements_by_tag_name("td")[2]             
                  Amount = float(cell.text.replace(' BTC',''))
                  cell = row.find_elements_by_tag_name("td")[4]
                  Lev = float(cell.text.replace('x',''))             
                  cell = row.find_elements_by_tag_name("td")[5]             
                  CutLoss = float(cell.text.replace(',',''))

                  cell = row.find_elements_by_tag_name("td")[6]               
                  lst = re.findall(r'\(.*?\)', cell.text.replace('%','')) 
                  PNL_t = ''.join(lst)
                  # print ("PNL_t", PNL_t)                  
                  PNL = float(PNL_t.replace('(','').replace(')',''))

                  sleep(1) # 1 secs delay here
                  break

        else: 
            print ('No any open positions found')
            return False
        
        if ( Amount > 0 ):
            print ("Found position LONG:", Amount, CutLoss, PNL, Lev)
            sleep(1)
            return LongPosition(Amount, CutLoss, PNL, Lev)

        else:   
            print ('No open LONG positions found')
            sleep(1)
            return False

   except ElementClickInterceptedException:
        print ('Unable to click on open positions')
        #driver.refresh
        sleep(15) # 5 secs delay here
        return False

   except TimeoutException:
        print ('Timeout')
        return False

   finally:
        sleep(1) # 1 secs delay here
##########################################################################################################
def OpenedPositionsShort(driver):

   ShortPosition = namedtuple ("ShortPosition", ["Amount", "CutLoss", "PNL", "Lev"])

   Amount = 0.0
   CutLoss = 0.00
   Lev = 0.0
   PNL = 0.00
   PNL_t = ''

   try:
        print ('Opened SHORT Positions test is running')
        sleep(1)
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"#tpositions")]'))   
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()
        sleep(1)

        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tbPositionList"]/tr'))   
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        sleep(1)

        row_count = len(driver.find_elements(By.XPATH, '//*[@id="tbPositionList"]/tr'))
        #column_count = len(driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr/td"))
        if row_count > 0 :

           for row in driver.find_elements(By.XPATH, '//*[@id="tbPositionList"]/tr'): 
               positionDirection = row.find_elements(By.TAG_NAME, "td")[1]

               if positionDirection.text == "DOWN" :
                  cell = row.find_elements_by_tag_name("td")[2]             
                  Amount = float(cell.text.replace(' BTC',''))
                  cell = row.find_elements_by_tag_name("td")[4]
                  Lev = float(cell.text.replace('x',''))             
                  cell = row.find_elements_by_tag_name("td")[5]             
                  CutLoss = float(cell.text.replace(',',''))   

                  cell = row.find_elements_by_tag_name("td")[6]               
                  lst = re.findall(r'\(.*?\)', cell.text.replace('%','')) 
                  PNL_t = ''.join(lst)
                  # print ("PNL_t", PNL_t)                  
                  PNL = float(PNL_t.replace('(','').replace(')',''))
                  
                  sleep(1) # 1 secs delay here             
                  break

        else: 
            print ('No any open positions found')
            sleep(1)
            return False

        if ( Amount > 0 ):
            print ("Found position SHORT:", Amount, CutLoss, PNL, Lev)
            sleep(1)
            return ShortPosition(Amount, CutLoss, PNL, Lev)
        else:
            print ('No open SHORT positions found')
            sleep(1)
            return False

   except ElementClickInterceptedException:
        print ('Unable to click on open positions')
        #driver.refresh
        sleep(15) # 5 secs delay here
        return False

   except TimeoutException:
        print ('Timeout')
        return False

   finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
# 1st time login
def DoLogIn(driver):

    try:
        print ('Do Login element is running')      
        # 3 | click | linkText=Login |  | 
        driver.find_element(By.LINK_TEXT, "Login").click()
        sleep(3) # 1 secs delay here
        driver.find_element(By.ID, "login_name").click()
        sleep(3) # 1 secs delay here
        driver.find_element(By.ID, "login_name").send_keys("xxx.xxx@gmail.com")
        sleep(3) # 1 mins delay here
        driver.find_element(By.ID, "login_pass").click()
        sleep(3) # 1 mins delay here
        driver.find_element(By.ID, "login_pass").send_keys("yyy")
        sleep(3) # 1 secs delay here
        driver.find_element(By.ID, "btn-login").click()
        sleep(3) # 1 secs delay here
        return True

    except TimeoutException:
        print ('Timeout')
        return None   
    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def TestLogIn(driver):
# Test name: logged out state

    try:
        print ('Login element test is running')  
        sleep(1)
        WebDriverWait(driver, TIME_TIMEOUT).until(EC.presence_of_element_located((By.LINK_TEXT, "Login"))   
        )
        return True

    except NoSuchElementException:
        print ('Login element not found')
        return False
    except TimeoutException:
        print ('Timeout')
        return False
    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def TestLogOut(driver):
# Test name: logged in state
    try:
        print ('Logout element test is running')  
        sleep(1)
        WebDriverWait(driver, TIME_TIMEOUT).until(EC.presence_of_element_located((By.LINK_TEXT, "Logout"))   
        )
        return True

    except NoSuchElementException:
        print ('Logout element not found')
        return False
    except TimeoutException:
        print ('Timeout')
        return False 
    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def CancelOrderLong(driver):
# Cancel ALCM limit orders 1 order at a time
    
    try:
        print ('Canceling Order LONG is running')
        sleep(1)
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"#topenorders")]'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()
        sleep(1)

        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        sleep(1)

        row_count = len(driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        #column_count = len(driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr/td"))
        if row_count > 0 :

           for row in driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'):

            rowType = row.find_elements_by_tag_name("td")[2]
            if rowType.text == "BUY" :

               OrderDirection = row.find_elements_by_tag_name("td")[1]         

               if ( OrderDirection.text == "UP" ):

                  cell = row.find_elements_by_tag_name("td")[7] # last cell
                  if cell.text == "Cancel" :
                     cell.click()
                     sleep(1)
                     break

           return True

        else:                     
             print ('No any open orders found')
             sleep(1)
             return False  

    except ElementClickInterceptedException:
        print ('Unable to click on open orders tab')
        #driver.refresh
        sleep(15) # 5 secs delay here
        return False

    except TimeoutException:
        print ('Timeout')
        return False 
    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def CancelOrderShort(driver):
# Cancel ALCM limit orders 1 order at a time
    
    try:
        print ('Canceling Order SHORT is running')
        sleep(1)
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"#topenorders")]'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()
        sleep(1)

        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        sleep(1)

        row_count = len(driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        #column_count = len(driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr/td"))
        if row_count > 0 :

           for row in driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'):

            rowType = row.find_elements_by_tag_name("td")[2]
            if rowType.text == "BUY" :

               OrderDirection = row.find_elements_by_tag_name("td")[1]         

               if ( OrderDirection.text == "DOWN" ):
                  cell = row.find_elements_by_tag_name("td")[7] # last cell
                  if cell.text == "Cancel" :
                     cell.click()
                     sleep(1)
                     break

           return True 

        else:                     
             print ('No any open orders found')
             sleep(1)
             return False  

    except ElementClickInterceptedException:
        print ('Unable to click on open orders tab')
        #driver.refresh
        sleep(15) # 15 secs delay here
        return False

    except TimeoutException:
        print ('Timeout')
        return False

    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def SubmitOrder(driver, Amount, Price, Lev, Type):
# Lev not implemented yet - 1x only
    try:
        OrderAmount = str(Amount)
        OrderPrice = str(Price)
        OrderType = str(Type)

        print ("Submitting ALCM Limit Order:", OrderType, OrderAmount, OrderPrice, Lev, OrderType)       
        sleep(1) # 1 secs delay here        
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.NAME, "leverage_number"))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()    
        sleep(1)

        #optional 5x lev ALCM but not today
        driver.find_elements_by_css_selector("input[type='radio'][value='1x']")[0].click()        
        sleep(2) # 2 secs delay here

        # limit order
        fillTypeorder = driver.find_element_by_link_text("Limit")
        fillTypeorder.click()
        sleep(2) # 2 secs delay here

        # ammo
        amount = driver.find_element(By.ID, "amountValue")
        amount.click()
        sleep(1)
        amount.clear()
        amount.send_keys(OrderAmount)         
        sleep(1) # 2 secs delay here

        # order price 
        price = driver.find_element(By.ID, "priceValue")
        price.click()
        sleep(1)
        price.clear()
        sleep(1)
        price.send_keys(OrderPrice)
        sleep(1) # 2 secs delay here

        # fire order up - LONG 
        if ( OrderType == "LONG" ): 
           orderUp = driver.find_element_by_xpath("//a[@class='btn btn-up']")
           orderUp.click()         
           sleep(2) # 1 secs delay here

        # fire order down - SHORT 
        if ( OrderType == "SHORT" ): 
           orderDown = driver.find_element_by_xpath("//a[@class='btn btn-down']")
           orderDown.click()
           sleep(2) # 1 secs delay here

        element = WebDriverWait(driver, TIME_TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#popOrderNoti .alert-close"))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()    
        sleep(1) # 1 secs delay here

        return True

    except NoSuchElementException:
        #driver.refresh
        sleep(15) # 5 secs delay here

    except TimeoutException:
        print ('Timeout')
        return False 

    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def OpenedOrdersLong(driver):

    OrderLong = namedtuple ("OrderLong", ["Amount", "Price", "Lev"])
    
    Amount = 0.0
    Price = 0.00
    Lev = 0.0

    try:
        print ('Open Orders LONG test is running')  
        sleep(1)        
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"#topenorders")]'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()
        sleep(1)

        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        sleep(1)

        row_count = len(driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        #column_count = len(driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr/td"))
        if row_count > 0 :

           for row in driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'):

            orderType = row.find_elements_by_tag_name("td")[2]
            if orderType.text == "BUY" :

               OrderDirection = row.find_elements_by_tag_name("td")[1]         

               if OrderDirection.text == "UP" :
                  cell = row.find_elements_by_tag_name("td")[3]                
                  Amount = float(cell.text.replace(' BTC',''))
                  cell = row.find_elements_by_tag_name("td")[4]                
                  Price = float(cell.text.replace(',',''))
                  cell = row.find_elements_by_tag_name("td")[6]
                  Lev = float(cell.text.replace('x',''))                
                  sleep(1) # 1 secs delay here
                  break

            elif orderType.text == "SELL":
                 print ("Found unattended sell order, please check")
                 sleep(1)
                 return False 
        else:                     
             print ('No any open orders found')
             sleep(1)
             Amount = 0
             return False

        if ( Amount > 0 ): 
           print ("Found order LONG: ", Amount, Price, Lev)
           sleep(1)        
           return OrderLong(Amount, Price, Lev)                     
           
        else:
           print ('No open orders LONG found')
           sleep(1)
           return False 

    except ElementClickInterceptedException:
        print ('Unable to click on open orders tab')
        #driver.refresh
        sleep(15) # 5 secs delay here
        return False

    except TimeoutException:
        print ('Timeout')
        return False 

    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def OpenedOrdersShort(driver):

    OrderShort = namedtuple ("OrderShort", ["Amount", "Price", "Lev"])

    Amount = 0.0
    Price = 0.00
    Lev = 0.0

    try:
        print ('Open Orders SHORT test is running')  
        sleep(1)
        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"#topenorders")]'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        element.click()
        sleep(1)

        element = WebDriverWait(driver, TIME_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        )
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        sleep(1)

        row_count = len(driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'))
        #column_count = len(driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr/td"))
        if row_count > 0 :

           for row in driver.find_elements(By.XPATH, '//*[@id="tbOpenOrderList"]/tr'):

            orderType = row.find_elements_by_tag_name("td")[2]
            if orderType.text == "BUY" :

               OrderDirection = row.find_elements_by_tag_name("td")[1]         

               if OrderDirection.text == "DOWN" :
                  cell = row.find_elements_by_tag_name("td")[3]                
                  Amount = float(cell.text.replace(' BTC',''))
                  cell = row.find_elements_by_tag_name("td")[4]                
                  Price = float(cell.text.replace(',',''))
                  cell = row.find_elements_by_tag_name("td")[6]
                  Lev = float(cell.text.replace('x',''))
                  sleep(1)
                  break

            elif orderType.text == "SELL":
                 print ("Found unattended sell order , please check")
                 sleep(1)
                 return False

        else: 
            print ('No any open orders found')            
            Amount = 0
            sleep(1)
            return False

        if ( Amount > 0 ): 
            print ("Found order SHORT :", Amount, Price, Lev)
            sleep(1)
            return OrderShort(Amount, Price, Lev)
        else:   
            print ('No open orders SHORT found')
            sleep(1)
            return False

    except ElementClickInterceptedException:
        print ('Unable to click on open orders')
        #driver.refresh
        sleep(15) # 5 secs delay here
        return False

    except TimeoutException:
        print ('Timeout')
        return None   
    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
def PageRefresh(driver):
    try:
            ldriver = driver      
            ldriver.refresh()
            ldriver.set_window_position(100, 20)
            ldriver.set_window_size(1600, 900)
            sleep(15) # delay here1

            ldriver.execute_script("document.body.style.zoom = '100%'")
#            ldriver.execute_script('document.body.style.MozTransform = "scale(0.90)";')
            ldriver.execute_script('document.body.style.MozTransformOrigin = "0 0";')    

    except TimeoutException:
        print ('Timeout')
        return None   
    finally:
        sleep(1) # 1 secs delay here

##########################################################################################################
##########################################################################################################
if __name__ == '__main__':
# do something       

    #profile = webdriver.FirefoxProfile()
    #profile.set_preference('browser.window.width',0)
    #profile.set_preference('browser.window.height',0)
    #profile.update_preferences() 
    CurrentExternalIP = urllib.request.urlopen('https://ident.me').read().decode('utf8')
    print('Checked CurrentExternalIP=',CurrentExternalIP)

    if (CurrentExternalIP != DefaultExternalIP):
       print ('CurrentExternalIP != DefaultExternalIP')
       driver.quit()
       sys.exit()
    
    print("OS name = ", os.name )

    if (os.name == 'nt'):
       fp = webdriver.FirefoxProfile("C:\\Users\\USER1\\06y3ok33.Profile1")

    else:
       fp = webdriver.FirefoxProfile("/home/zhenya/.mozilla/firefox/2ykva0d2.profile1")
     
    driver = webdriver.Firefox(fp)
    driver.get("https://www.bitseven.com/Trading")
    driver.implicitly_wait(5) # seconds
    
    print ('Starting browser refresh')     

    PageRefresh(driver)
    
    #stupid XRP warning
    try:
      element = driver.find_element(By.LINK_TEXT, "Close")
      actions = ActionChains(driver)
      actions.move_to_element(element).perform()
      driver.find_element(By.LINK_TEXT, "Close").click()
    except:
      pass
    
# logout window / login attempt sanity check
##########################################################################################################     

if TestLogOut(driver) is True:
     print ('Already logged in')

elif TestLogIn(driver) is True:               
     print ('Starting log in section')              
     DoLogIn(driver)
     sleep(5) # delay here
     driver.get("https://www.bitseven.com/Trading")
     sleep(5) # delay here
     if TestLogOut(driver) is False :
        print ('Unknown log in error')
        driver.quit()
        sys.exit()
     else:
        print ('Logged in !')      

sleep(1) # delay here

##########################################################################################################
while True:

   time.sleep(1)   
   os.system('cls' if os.name == 'nt' else 'clear')

   print (30 * '-')
   print ("   M A I N - M E N U")
   print (30 * '-')
   print ("1. Orders management(default) ")
   print ("2. Quit")
   print ("3. Reboot")
   print ("Will run option 1 in a 30 secs")  
   print ("\n")  
   
   ## Wait for valid input choice == 1 default
   try:        
     choice = inputimeout(prompt='enter values 1-3 \n', timeout=30)

     if ( choice == '1' ):
        time.sleep(1)  
        pass
     elif ( choice == '2'):
        print ("Quitting...")       
        time.sleep(1)
        driver.quit()     
        sys.exit()
     elif ( choice == '3' ):
        print ("Rebooting the server...")
        #reboot

   except TimeoutOccurred:
     choice = 1

   finally:
     print("choice:", choice)      
   ##########################################################################################################

   ##########################################################################################################
   try:    
          
      print ("\n == Checking LONG Positions == ")
      
      if ( OpenedPositionsLong(driver) is not False ):
          LongPositionAmount, LongPositionCutLoss, LongPositionPNL, LongPositionLev = OpenedPositionsLong(driver)
      
      if ( LongPositionAmount > 0 ):
          isLongPosition = True
      
      sleep(1) # delay here

      # Checking PNL for any position first  
      if ( isLongPosition is True ) and ( IsSellLong() is True ):
         print ("Selling position LONG")
         isLongPosition = False


      # Checking ALCM LONG limit Orders      
      if ( OpenedOrdersLong(driver) is not False) and ( isLongPosition is True ):
           OrderLongAmount, OrderLongPrice, OrderLongLev = OpenedOrdersLong(driver)         
      
           diff = ( OrderLongPrice - LongPositionCutLoss)
           print ("diff", diff)
      
           if ( diff == 10.0 ):
              print ("and it is matching ALCM limit order LONG :", OrderLongAmount, OrderLongPrice, OrderLongLev)
              isLongALCM = True
      
           else:
              print ("for whatever reason is not matching ALCM limit order LONG :", OrderLongAmount, OrderLongPrice, OrderLongLev)
              isLongALCM = False
      
           sleep(1) # delay here
      
      # ALCM submitting   : 1 ALCM limit order is not present for existing position 
      #                     2 Position is non existent for existing ALCM limit order    
      
      print ("Missing ALCM limit orders verification and submission")  
      
      if ( isLongALCM is True ) and ( isLongPosition is True ):
         print ("LONG Position has matching ALCM LONG limit order, moving on...")
      
      elif ( isLongALCM is False ) and ( isLongPosition is True ):
           print ("Submitting ALCM limit order for LONG Position ")
           LongPositionPrice = float(LongPositionCutLoss + 10)
      
           if ( SubmitOrder(driver, LongPositionAmount, LongPositionPrice, 1, 'LONG') is True ):                        
              print ("Submitted ALCM limit order for LONG Position ")
              print ("Verifying ALCM limit order for LONG Position")
              sleep(1) # delay here                  
              if ( OpenedOrdersLong(driver) is not False ):         
                 isLongALCM = True
           else:
              print ("Submitting order error")
      
           sleep(1) # delay here         
      
      ###################################################################################################
      
      print ("\n == Checking SHORT Positions == ")
      
      if ( OpenedPositionsShort(driver) is not False ):        
          ShortPositionAmount, ShortPositionCutLoss, ShortPositionPNL, ShortPositionLev = OpenedPositionsShort(driver)
      
      if ( ShortPositionAmount > 0 ):
          isShortPosition = True
      
      sleep(1) # delay here     
      
      # Checking PNL for any position first  
      if ( isShortPosition is True ) and ( IsSellShort() is True ):
         print ("Selling position SHORT")
         isShortPosition = False


      # Checking ALCM SHORT limit Orders      
      if ( OpenedOrdersShort(driver) is not False) and ( isShortPosition is True ):
           OrderShortAmount, OrderShortPrice, OrderShortLev = OpenedOrdersShort(driver)
      
           diff = (ShortPositionCutLoss - OrderShortPrice)
           print ("diff", diff)
      
           if ( diff == 10.0 ):
               print ("and it is matching ALCM limit order SHORT :", OrderShortAmount, OrderShortPrice, OrderShortLev)
               isShortALCM = True
      
           else:     
               print ("for whatever reason is not matching as ALCM limit order SHORT :", OrderShortAmount, OrderShortPrice, OrderShortLev)
               isShortALCM = False
      
      sleep(1) # delay here
      
      # ALCM submitting   : 1 ALCM limit order is not present for existing position 
      #                     2 Position is non existent for existing ALCM limit order    
      
      if ( isShortALCM is True ) and ( isShortPosition is True ):
         print ("SHORT Position has matching ALCM limit order, moving on...")       
         
      elif ( isShortALCM is False ) and ( isShortPosition is True ):
           print ("Submitting ALCM limit order for SHORT Position ")
           ShortPositionPrice = float(ShortPositionCutLoss - 10)
      
           if ( SubmitOrder(driver, ShortPositionAmount, ShortPositionPrice, 1, 'SHORT') is True):                        
              print ("Submitted ALCM limit order for SHORT Position ")
              print ("Verifying ALCM limit order for SHORT Position")
              sleep(1) # delay here         
              if ( OpenedOrdersShort(driver) is not False ):         
                 isShortALCM = True
           else:
              print ("Submitting order error")       
      
      sleep(1) # delay here         
      
      ###################################################################################################
      # Checking and canceling ALCM limit orders for nonexisting longs position / has been sold      
      print ("ALCM limit orders for nonexisting positions housekeeping")  
      # PageRefresh(driver) - no need to run this every time      
      sleep(1)

      print ("isLongPosition:", isLongPosition)
      
      if ( isLongPosition is False ):       
          
         # 2nd check for limit orders               
         if ( OpenedOrdersLong(driver) is not False ):
              OrderLongAmount, OrderLongPrice, OrderLongLev = OpenedOrdersLong(driver)
              isLongALCM = True
      
              print ("Looks like ALCM limit order LONG doesn't have LONG position matching")
              print ("Canceling ALCM LONG limit order")
              sleep(1) # 1 secs delay here
      
              if ( CancelOrderLong(driver) is True ):
                 print ("ALCM LONG limit order canceled")
                 sleep(1)
              else:
                 print ("order cancel failed")
      #
         
      sleep(1) # delay here         

      ###################################################################################################
      # Checking and canceling ALCM limit orders for nonexisting short position / has been sold      
      print ("ALCM limit orders for nonexisting positions housekeeping")  
      # PageRefresh(driver) - no need to run this every time
      print ("isShorPosition:", isShortPosition)
      
      if ( isShortPosition is False ):
         # 2nd check 
         
         if ( OpenedOrdersShort(driver) is not False ): 
              OrderShortAmount, OrderShortPrice, OrderShortLev = OpenedOrdersShort(driver)
              isShortALCM = True
      
              print ("Looks like ALCM limit order SHORT doesn't have SHORT position matching")       
              print ("Canceling ALCM SHORT limit order")
              sleep(1) # 1 secs delay here
      
              if ( CancelOrderShort(driver) is True ):
                 print ("ALCM SHORT limit order canceled")
                 sleep(1) # 1 secs delay here
              else:
                 print ("order cancel failed")    
      
      sleep(1) # delay here                        
                      
          
   ##########################################################################################################
   except TimeoutException:
        print ('Timeout')
           
   finally:

   #   print(dir())
         print ('All steps completed')           
   # happy ending here
   ##########################################################################################################
      
