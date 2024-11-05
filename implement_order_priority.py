import asyncio
from asyncio import sleep as async_sleep, Lock, Semaphore
import random


class Pizza:
	def __init__(self, pizza_id, priority='Normal'):
		self.pizza_id = pizza_id
		self.status = 'in_fridge'
		self.priority = priority
	
	STATUSES = (
		'in_fridge',
		'to_make',
		'made',
		'in_oven',
		'baked',
		'to_pack',
		'to_deliver',
		'delivered'
	)


class PriorityQueue:
	def __init__(self):
		self._urgent = []
		self._normal = []
		self._unfinished_tasks = 0
		self._finished = asyncio.Event()
		self._finished.set()
	
	async def put(self, item):
		if item.priority == 'Urgent':
			self._urgent.append(item)
		else:
			self._normal.append(item)
		
		self._unfinished_tasks += 1
		self._finished.clear()
	
	async def get(self):
		if self._urgent:
			return self._urgent.pop(0)
		elif self._normal:
			return self._normal.pop(0)
		else:
			raise asyncio.QueueEmpty
	
	def task_done(self):
		self._unfinished_tasks -= 1
		if self._unfinished_tasks == 0:
			self._finished.set()
	
	async def join(self):
		await self._finished.wait()
	
	def empty(self):
		return not (self._urgent or self._normal)


class PizzaMaker:
	def __init__(self, number):
		self.lock = Lock()
		self.active_pizza = None
		self.number = number
	
	async def make_busy(self, seconds, pizza):
		await self.lock.acquire()
		self.active_pizza = pizza
		await async_sleep(seconds)
		self.lock.release()
	
	async def get_ingredients_from_fridge(self, pizza):
		await self.make_busy(1, pizza)
		pizza.status = 'to_make'
		await make_queue.put(pizza)
		fridge_queue.task_done()
	
	async def make_pizza(self, pizza):
		await self.make_busy(2, pizza)
		pizza.status = 'made'
		await put_into_oven_queue.put(pizza)
		make_queue.task_done()
	
	async def put_into_oven(self, pizza, ovens_semaphore):
		await ovens_semaphore.acquire()
		await self.make_busy(1, pizza)
		pizza.status = 'in_oven'
		await oven_queue.put(pizza)
		put_into_oven_queue.task_done()
	
	async def take_out_of_oven(self, pizza, ovens_semaphore):
		await self.make_busy(1, pizza)
		ovens_semaphore.release()
		pizza.status = 'to_pack'
		await pack_queue.put(pizza)
		oven_queue.task_done()
	
	async def pack_pizza(self, pizza):
		await self.make_busy(1, pizza)
		pizza.status = 'to_deliver'
		await deliver_queue.put(pizza)
		pack_queue.task_done()
	
	async def deliver_pizza(self, pizza):
		await self.make_busy(1, pizza)
		pizza.status = 'delivered'
		deliver_queue.task_done()
	
	async def do_the_job(self, ovens_semaphore):
		while True:
			if not deliver_queue.empty():
				pizza = await deliver_queue.get()
				await self.deliver_pizza(pizza)
			elif not pack_queue.empty():
				pizza = await pack_queue.get()
				await self.pack_pizza(pizza)
			elif not take_out_of_oven_queue.empty():
				pizza = await take_out_of_oven_queue.get()
				await self.take_out_of_oven(pizza, ovens_semaphore)
			elif not put_into_oven_queue.empty() and not ovens_semaphore.locked():
				pizza = await put_into_oven_queue.get()
				await self.put_into_oven(pizza, ovens_semaphore)
			elif not make_queue.empty():
				pizza = await make_queue.get()
				await self.make_pizza(pizza)
			elif not fridge_queue.empty():
				pizza = await fridge_queue.get()
				await self.get_ingredients_from_fridge(pizza)
			else:
				self.active_pizza = None
				await async_sleep(1)


class Oven:
	def __init__(self):
		self.lock = Lock()
	
	async def do_the_job(self):
		while True:
			if not oven_queue.empty():
				pizza = await oven_queue.get()
				await async_sleep(4)
				pizza.status = 'baked'
				await take_out_of_oven_queue.put(pizza)
				oven_queue.task_done()
			else:
				await async_sleep(0.1)


fridge_queue = PriorityQueue()
make_queue = PriorityQueue()
put_into_oven_queue = PriorityQueue()
take_out_of_oven_queue = PriorityQueue()
pack_queue = PriorityQueue()
deliver_queue = PriorityQueue()
oven_queue = PriorityQueue()


async def console_job(pizzas, workers):
	while True:
		print('\033[H\033[J')
		for pizza in pizzas:
			active_worker = next((worker for worker in workers if worker.active_pizza == pizza), None)
			status_order = Pizza.STATUSES.index(pizza.status)
			print(
				f'Pizza {pizza.pizza_id} [{pizza.priority}]: {"*" * status_order}{"-" * (len(Pizza.STATUSES) - status_order - 1)}',
				end='')
			print(f' ({pizza.status})', end='')
			if active_worker:
				print(f' (Worker {active_worker.number})', end='')
			print()
		print()
		await async_sleep(1)


async def main():
	print("Welcome to the pizza factory!")
	workers_amount = int(input('Enter the amount of workers: '))
	pizza_amount = int(input('Enter the amount of pizzas: '))
	ovens_amount = int(input('Enter the amount of ovens: '))
	
	ovens = [Oven() for _ in range(ovens_amount)]
	ovens_semaphore = Semaphore(ovens_amount)
	workers = [PizzaMaker(i + 1) for i in range(workers_amount)]
	
	worker_tasks = [asyncio.create_task(worker.do_the_job(ovens_semaphore)) for worker in workers]
	oven_tasks = [asyncio.create_task(oven.do_the_job()) for oven in ovens]
	
	pizzas = [Pizza(i + 1, priority=random.choice(['Normal', 'Urgent'])) for i in range(pizza_amount)]
	
	fridge_tasks = [fridge_queue.put(pizza) for pizza in pizzas]
	
	console_task = asyncio.create_task(console_job(pizzas, workers))
	
	await asyncio.gather(*fridge_tasks)
	
	await make_queue.join()
	await fridge_queue.join()
	await put_into_oven_queue.join()
	await take_out_of_oven_queue.join()
	await oven_queue.join()
	await pack_queue.join()
	await deliver_queue.join()
	
	for worker_task in worker_tasks:
		worker_task.cancel()
	
	for oven_task in oven_tasks:
		oven_task.cancel()
	
	console_task.cancel()
	
	await asyncio.gather(*worker_tasks, return_exceptions=True)
	await asyncio.gather(*oven_tasks, return_exceptions=True)
	await console_task


if __name__ == '__main__':
	asyncio.run(main())
